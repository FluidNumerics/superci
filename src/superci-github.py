#!/usr/bin/env python

from github import Github
from github import Auth
import subprocess
import shlex
import yaml
import os
import sys
from datetime import datetime
import logging
import argparse
import json

logdir=os.getenv('HOME')+'/.superci/logs'

def check_if_commit_is_tested(repository,commitsha):
    """
    Checks the history (if any) to see if the commit has already been tested
    """
    runlog = f"{logdir}/{repository}/superci-log.yaml"

    if os.path.isfile(runlog): # check if file exists
        with open(f'{runlog}', 'r') as file:
            logs = yaml.safe_load(file)

        for l in logs: # loop over list of log entries
            if l['commit'] == commitsha:
                return True
        
        # If we get to this point, the commitsha with any state has not been found and we ought to test it
        return False
    else:
        return None

def clone_repository(repo_url,workspace_dir,branch,commitsha):
    """
    Clones a specific commit of the repository from repo_url to 
    workspace_dir. Returns the path to the repository if successful,
    otherwise returns None
    """

    try:
        subprocess.run(shlex.split(f'git clone --single-branch --branch={branch} {repo_url} {workspace_dir}'))
        subprocess.run(shlex.split(f'git checkout {commitsha}'), cwd={workspace_dir})
        return workspace_dir
    except:
        return None
    

def create_workspace(params, build_id):
    """
    Digests the input yaml steps and creates bash scripts for each step
    """

    workspace_root = params['config']['workspace_root']
    repository = params['config']['repository']
    workspace_dir = f"{workspace_root}/{repository}/{build_id}"
    if not os.path.exists(workspace_dir):
        logging.info(f"Creating workspace directory: {workspace_dir}")
        os.makedirs(workspace_dir)
    
    return workspace_dir

def generate_batch_scripts(params, workspace_dir):
    """
    Digests the input yaml steps and creates batch scripts for each step
    """

    stepid = 0
    build_steps = []
    for step in params['steps']:
        sbatch_opts = step['sbatch_options']
        modules = step['modules']
        env = step['env']
        commands = step['commands']

        script="#!/bin/bash\n"

        if sbatch_opts:
            for opt in sbatch_opts:
                script+=f"#SBATCH {opt}\n"
        # Add stderr and stdout options
        script+=f"#SBATCH -o {workspace_dir}/step-{stepid:03}.out\n"
        script+=f"#SBATCH -e {workspace_dir}/step-{stepid:03}.err\n"

        script+= "\n"
        # Load modules
        if modules:
            script+="module purge\n"
            for module in modules:
                script+=f"module load {module} \n"

        script+= "\n"
        # Set environment variables
        script+=f"export WORKSPACE={workspace_dir}\n"
        for var in env.keys():
            script+=f"export {var}={env[var]}\n"

        script+= "\n"
        # Add commands to run
        for command in commands:
            script+=f"{command}\n"

        with open(f"{workspace_dir}/step-{stepid:03}.sh","w+") as f:
            f.writelines(script)

        build_steps.append({"name":step['name'],"script":f"{workspace_dir}/step-{stepid:03}.sh"})
        stepid+=1

    return build_steps

def run_build_steps(build_steps):
    """
    Runs the list of build steps and returns a list of build step names paired to exit codes
    """

    if len(build_steps) > 1:
        logging.warning("Job dependencies are not currently set up between build steps. Use at your own risk.")

    # [TO DO] : Check if `sbatch` command exists. Otherwise, run commands locally
    launcher = "/usr/bin/sbatch --wait"

    step_results = []
    aggregate_status = 0
    for step in build_steps:
        batch_script = step['script']
        name = step['name']
        logging.info(f"Running job build step : {name}")
        logging.info(f"{launcher} {batch_script}")
        proc = subprocess.run(shlex.split(f"{launcher} {batch_script}"), 
                capture_output=True)
        step_results.append({'name':name,'exit_code':proc.returncode})
        aggregate_status+=abs(proc.returncode)
        if proc.returncode != 0:
            logging.warning(f"Job build step failed : {name}")
            break

    return step_results, aggregate_status

def update_commit_status(repository,commitsha,token,state,description):
    """
    Updates the
    repository - in the format of {owner}/{repository}
    state - must be one of error, failure, pending, success
    """
    import requests


    headers = {'Accept': 'application/vnd.github+json',
               'Authorization': f'Bearer {token}',
               'X-GitHub-Api-Version': '2022-11-28'}
    payload = {"state":state,"target_url":"https://example.com/build/status","description":description,"context":"continuous-integration/superci"}

    url = f"https://api.github.com/repos/{repository}/statuses/{commitsha}"
    r = requests.post(url, data=json.dumps(payload), headers=headers)
    return r

def pr_workflow(params,repo,token):
    """
    Checks all open pull requests in your repository that are targeting params.config.branch
    For each pull request that matches this criteria, we pull information on the last commit
    on the repository.

    If superci detects that we have run tests for this commit, nothing is done.

    If superci detects that we have not run test for this commit, and the date of the last
    commit precedes the date of a comment whose body is equal to "/superci" (without quotes)
    then we schedule a test to run using the template batch script and the contents of the 
    params.steps .

    For any other scenario, nothing is done.

    """

    # Get pull requests that are going to the main branch
    repo_url = f'https://github.com/{params["config"]["repository"]}'
    pulls = repo.get_pulls(state='open', sort='created', base=params['config']['branch'])
    current_datetime = datetime.now()
    
    for p in pulls:

        branch = p.head.ref
        last_commit = p.get_commits()[p.commits - 1]
        commit_date = last_commit.commit.committer.date
        commit_is_tested = check_if_commit_is_tested(params['config']['repository'],last_commit)

        if not commit_is_tested:
            for c in p.get_issue_comments():
                if c.body == "/superci" and c.created_at > commit_date:

                    # [TO DO] : Get author of comment and compare with repository owners/admins

                    logging.info(f"Preparing to test git sha: {last_commit.sha}")
                    build_id = last_commit.sha[0:7]
                    logging.info(f"build id : {build_id}")

                    # Set the commit status to pending
                    resp = update_commit_status(params['config']['repository'],
                            last_commit.sha,token,'pending','Waiting for tests to complete')
                    logger.info(resp.text)

                    workspace_dir = create_workspace(params, build_id)
                    repo = clone_repository(repo_url,workspace_dir,branch,last_commit.sha)
                    build_steps = generate_batch_scripts(params, workspace_dir)
                    step_results, aggregate_status = run_build_steps(build_steps)

                    if aggregate_status != 0:
                        logging.warning("Build/Test workflow failure detected")
                        # Set the commit status to failure
                        resp = update_commit_status(params['config']['repository'],
                                last_commit.sha,token,'failure','One or more of the build steps failed')
                        logger.info(resp.text)
                    else:
                        resp = update_commit_status(params['config']['repository'],
                                last_commit.sha,token,'success','Tests successful')
                        logger.info(resp.text)

                    #[TO DO] : write_run_log(params["config"]["repository"],branch,last_commit,current_datetime,aggregate_status)

                    

def parse_cli():
    """
    Parses command line options and returns args object
    """
    parser = argparse.ArgumentParser(description='Poll your github repository, check for builds and run them')
    parser.add_argument('-c','--config', help='Fully qualified path to a superci configuration file.', default='./examples/demo.yml')
    return parser.parse_args()

def configure_logging():
    """
    Sets up the directories for superci logging and configures the logging module accordingly.
    Logs will always go to ${HOME}/.superci/logs
    """


    if not os.path.exists(logdir):
        os.makedirs(logdir)

    # Set Debug (and higher) messages to file
    logging.basicConfig(filename=f"{logdir}/superci-github.log",
                        filemode='a',
                        format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                        datefmt='%H:%M:%S',
                        level=logging.DEBUG)

    # Set info messages to console
    # define a Handler which writes INFO messages or higher to the sys.stderr
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter('%(name)s %(levelname)s %(message)s')
    console.setFormatter(formatter)
    logging.getLogger().addHandler(console)

        


# main below
# ////////////////// #
def main():

    configure_logging()

    args = parse_cli()

    logging.info(f'Loading configuration file {args.config}')
    with open(args.config, 'r') as file:
        ciparams = yaml.safe_load(file)

    

    # Get the Github personal authenication token
    f = open(ciparams['config']['github_access_token_path'], "r")
    token = f.readline().strip()
    auth = Auth.Token(token)
    f.close()

    # Create a repository object
    repository = ciparams["config"]["repository"]
    g = Github(auth=auth)
    repo = g.get_repo(repository)
    
    # Kick off the PR workflow
    pr_workflow(ciparams,repo,token)

if __name__ == '__main__':
    main()




