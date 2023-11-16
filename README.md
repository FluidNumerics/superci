# Super(Simple)CI

Simple Continuous Integration tools for Super Computers.

This package was inspired by discussions at Pawsey Supercomputing Centre's PaCER Conference 2023.

**This package is highly experimental. We encourage you to try it out, contribute your ideas through discussion and pull requests!**

## Purpose
The intention of this package is to provide you with some tooling to accomplish the following
* Check your github repository for open pull requests to a desired base branch
* Check the pull request comment history for a comment with nothing more than just `/superci` from an authorized user
* Execute a build/test workflow using Slurm batch jobs on the most recent commit on the source branch just before the `/superci` comment 
* Report the build/test results back to the pull request through a build status update


## Get Started

You will need a [Github Personal Access Token](https://github.com/settings/tokens) associated with your account or organization.

> [!NOTE]
> This repository uses [PyGithub](https://pygithub.readthedocs.io/en/stable/introduction.html) as a dependency in order to integrate with the Github API.

> [!WARNING]  
> For organization owned repositories, you will see this error message if you did not create a personal access token with **fine-grained permissions**
> ```
> github.GithubException.GithubException: 
> 403 {"message": "`{Organization}` forbids access via a personal access token (classic). 
> Please use a GitHub App, OAuth App, or a personal access token with fine-grained permissions.", 
> "documentation_url": "https://docs.github.com/rest/repos/repos#get-a-repository"}
> ```

1. Clone this repository
```
git clone https://github.com/fluidnumerics/superci ~/superci
```

2. Install python requirements
```
cd ~/superci
conda create -n superci python=3.9
conda activate superci
pip install -r requirements.txt
```
3. Edit the `examples/armory.yml` file. Change the `config.github_access_token_path` to the path on your system that you have save your Github Private Access Token to. Change the `config.workspace_root` to a path on your system where you have read and write access to. Change the `config.repository` to a repository that you have access to. Change the `config.branch` to a base branch where you would like to require tests to run before merging.

4. On your repository, create a branch and open a pull request to the base branch specified in `config.branch`

5. Add a comment that just says `/superci`

5. Try the demo
```
python src/superci-github.py
```

5. If it breaks, you have some ideas, or you hate me, open an issue


## SuperCI schema
Like other CI systems, superci will ingest a markdown file (here, we use yaml) that will be used to execute a build/test workflow for your application, based on parameters provided in this file. A rough draft of the schema is given below.

* `steps` - List(object) - A list of steps that will each be converted to a batch job
* `step.name` - string - A human readable name for the step
* `step.sbatch_options` - List(string) - options to send to [`sbatch`]() for a given step.
* `step.modules` - List(string) - list of modules that will be loaded with `module load`. Leave empty if you don't use modules.
* `step.env` - Object - Set of key:value pairs that are used to set environment variables in your job. Keep in mind `WORKSPACE` is an environment variable defined for you that references the temporary working directory for your build.
* `step.commands` - List(string) - A list of commands that you want to run for this build step
* `config.repository` - string - The repository hosted on github (in `{owner}/{repo}` format) that you want to test
* `config.branch` - string - The head branch that requires testing before merging into with a pull request
* `config.github_access_token_path` - string - The full path on your HPC cluster where your github access token is located
* `config.workspace_root` - string - The directory where superci logs are written and where all of your build/test temporary working directories are created.



## Current Limitations
* There's tons of hard-coded stuff at the moment - this repository is currently set up to provide proof of concept in order to promote discussion and collaboration with others before going too far.
* Currently under development and hard-wired to create batch files for the `examples/armory.yml` input file
* Currently, we do not check for a list of repository owners/admins to verify authorized users who wrote the `/superci` comment. This is in the works!
* We can only run tests with a single step. More sophisticated tracking of job success and failure is necessary for jobs with dependencies to support multi-step builds.