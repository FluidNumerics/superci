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

You will need a [Github Personal Access Token](https://github.com/settings/tokens) associated with your account or organization. We recommend using a fine-grained access token with the following permissions
*  Read access to code and metadata
*  Read and Write access to actions, commit statuses, discussions, issues, and pull requests

The personal access token value needs to be saved to a file on the login node of an HPC cluster where you will run your tests.

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


> [!WARNING]  
> The example below assumes you are on a login node of an HPC cluster equipped with the Slurm job scheduler

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
3. Edit the `examples/demo.yml` file. Change the `config.github_access_token_path` to the path on your system that you have save your Github Private Access Token to. Change the `config.workspace_root` to a path on your system where you have read and write access to. Change the `config.repository` to a repository that you have access to. Change the `config.branch` to a base branch where you would like to require tests to run before merging.

4. On your repository, create a branch, copy this repositories `examples/superci.yml` to the root directory of your repository, commit the change, and open a pull request to the base branch specified in `config.branch`. Make any necessary changes to the `steps.sbatch_options` to fit your HPC cluster's configuration.

5. Add a comment to the pull request that just says `/superci`

6. Try the demo
```
python src/superci-github.py
```

7. If it breaks or you have some ideas [open an issue](https://github.com/FluidNumerics/superci/issues/new)

## Deploying SuperCI in practice
In practice, you likely want to "set and forget" for your CI system. On HPC systems equipped with the Slurm workload manager, you can use [`scrontab`](https://slurm.schedmd.com/scrontab.html) to configure a schedule to launch recurring batch jobs. You can leverage `scrontab` to regularly launch the `superci-github.py` application. This job itself does not require a lot of resources (one cpu only and less than 1G of RAM, likely).

## SuperCI schema
Like other CI systems, superci will ingest a markdown file (here, we use yaml) that will be used to execute a build/test workflow for your application, based on parameters provided in this file. With SuperCI, there are two yaml files that are used to configure runs. The first is a configuration file that you store on the login node of an HPC cluster (with a slurm job scheduler) where the `superci-github.py` program is run; this is called the "SuperCI service configuration". The second is the configuration file included in your application's github repository; this is called your applications "build/test configuration".
 
A rough draft of the schemas are given below

### SuperCI service configuration
* `config.repository` - string - The repository hosted on github (in `{owner}/{repo}` format) that you want to test
* `config.branch` - string - The head branch that requires testing before merging into with a pull request
* `config.github_access_token_path` - string - The full path on your HPC cluster where your github access token is located
* `config.workspace_root` - string - The directory where where all of your build/test temporary working directories are created.
* `config.superci_yaml` - string - Path, relative to your application repository's root directory where your build/test configuration is stored.
* `config.context` - string - The context label to use for the build. Often, this is used to indicate the platform or type of test you are running

### Build/Test configuration
* `steps` - List(object) - A list of steps that will each be converted to a batch job
* `step.name` - string - A human readable name for the step
* `step.sbatch_options` - List(string) - options to send to [`sbatch`]() for a given step.
* `step.modules` - List(string) - list of modules that will be loaded with `module load`. Leave empty if you don't use modules.
* `step.env` - Object - Set of key:value pairs that are used to set environment variables in your job. Keep in mind `WORKSPACE` is an environment variable defined for you that references the temporary working directory for your build.
* `step.commands` - List(string) - A list of commands that you want to run for this build step

## Miscellaneous 
Log files for `superci` are written under `${HOME}/.superci/logs`

## Current Limitations
* `grep TODO src/*` to see a list of to-do items 
* There's tons of hard-coded stuff at the moment - this repository is currently set up to provide proof of concept in order to promote discussion and collaboration with others before going too far.
* We assume `sbatch` is installed in `/usr/bin/sbatch`. We also need a fallback in case `sbatch` is not available (e.g. run locally)
* Commit statuses are pushed, which updates information on a pull request. [Checks](https://docs.github.com/en/rest/checks?apiVersion=2022-11-28) are not created, however, Checks would provide a way to push batch script stdout/stderr back to Github.
* Currently, we do not check for a list of repository owners/admins to verify authorized users who wrote the `/superci` comment. This is in the works!
* We can only run tests with a single step. More sophisticated tracking of job success and failure is necessary for jobs with dependencies to support multi-step builds.
