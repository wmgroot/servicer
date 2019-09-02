# Servicer #

Servicer is a configuration-based CI automation framework that runs inside popular CI platforms, such as Bitbucket Pipelines, Jenkins, and CircleCI.
Servicer may be the right tool to use if you find yourself in any these situations:
* Writing a lot of Bash to augment your CI/CD jobs.
* Have dependent services building from the same repository (common in mono-repos).
* Want to speed up your CI job times by building services in parallel, or avoiding building services that have not changed.

Core Features:
* Run and debug your CI jobs locally (very helpful for isolating or testing build issues before you deploy).
* CI provider agnostic configuration (make your build process portable between multiple CI providers).
* Map your branches and tags to independent service environments, allowing you to use an identical process to deploy production, testing, and development environments.
* Interpolate dynamic values that change from environment to environment, allowing you to re-use the same configuration for your environments.
* Configure intelligent Change Detection, to only build the services and dependencies you need for the changes made (great for mono-repos!).

Servicer executes a set of service-steps you define in `.servicer/services.yaml`. A servicer CI job will roughly do the following:
1. Normalize the current CI environment (by standardizing environment variables).
2. Determine the current Service Environment, if it exists.
3. Construct the complete servicer configuration (interpolating dynamic value tokens).
4. Determine which services can be ignored by Change Detection.
5. Build a dependency graph of remaining service-steps.
6. Execute each service-step in the order determined by the dependency graph, if it is appropriate for the current Service Environment.

Contributing
Servicer is an open-source project. Feel free to fork and open a PR at any time. Each PR should have an associated Issue linked for reference.

## Separation of Concerns ##
Servicer is separated into three main components: adapters, services, and the project environment.

_Adapters_ are interfaces that allow Servicer to use or interact with external systems, like Google Cloud Platform, GitHub, Jenkins, Docker, etc. Three kinds of adapters exist: CI adapters (for CI providers), auth adapters (to manage credentials), and service adapters (for everything else). These are written as reusable python modules, and are located in `servicer/builtin`.

_Configuration_ is the primary building block of your project. Services are defined in the `.servicer/services.yaml` file in your project, and these definitions include the configuration and commands needed to build, test and deploy each service. Additionally, dependencies may be defined to automate the order service-steps are executed in.

Your _project environment_ should contain environment variables for holding credentials and other secrets that should not be committed to source control. These can be configured on your CI tool, or, if you are running Servicer locally, from a `.servicer/*.env.yaml` file.

## Using Servicer ##
For the simplest use case, use the command below. With it, Servicer will execute every step for every service you've defined in `.servicer/services.yaml`.
```
servicer
```
If you want Servicer to execute all steps for one or more specific services, like my_docker_image and my_python_package, specify those services in the command.
```
servicer --service=my_docker_image,my_python_package
```
Steps, like build and unit_test, can also be specified.
```
servicer --step=build,unit_test
```
When combined, you can execute a single service-step:
```
servicer --service=my_docker_image --step=build
```
These commands can be run locally or in the context of a CI job.

By default, all service-step dependencies will also be executed. If you will like to disable this behavior, use the `--ignore_dependencies` flag.

If you would like to execute a test run of servicer without actually executing any service-steps, you can add the `--dry` flag.

To set the desired logging level (debug, info, warn, error), use the `--log_level` flag.

For a complete list of flags and options that can be provided to the `servicer` command, please see `servicer --help`.

## Configuration ##
By default, Servicer will look for `.servicer/services.yaml` at the root of your project. `servicer/builtin/defaults.yaml` (https://github.com/wmgroot/servicer/blob/master/servicer/builtin/defaults.yaml) contains default values and descriptions of the values you can provide in `.servicer/services.yaml`.

Within this section of the README, consider each of these subsections to compose the `services.yaml` on one project.

### Environment ###
The `environment` section of `services.yaml` will let you define environment variables that you're ok with existing in source control. Additionally, you can control the branch -> service_environment settings, allowing you to change the defaults. Consider the example below.

```
environment:
  # In this example, SERVICE_ENVIRONMENT will be `production` if the branch is `master`.
  # SERVICE_ENVIRONMENT will be `develop` if the branch is `develop`.
  # Otherwise, if the branch matches `env-*`, SERVICE_ENVIRONMENT will be the sanitized branch name.
  # If the CI provider supports tag based builds, servicer will also set the SERVICE_ENVIRONMENT if a version tag is found.
  mappings:
    - tag: '*.*.*'             # match a version tag -> 1.2.3
    - branch: master
      environment: production  # master -> production
    - branch: develop          # develop -> develop
    - branch: env-*            # env-my-branch -> env-my-branch

  # Define environment variables here.
  variables:
    FOO: BAR
    PROJECT_NAME: ${PRE_DEFINED_ENV_VAR}-plus-some
...
```
Servicer requires several environment variables to be configured which control the parameters of each service. Some of these environment variables will be automatically pulled from your CI environment and standardized by the CI Adapter it is using. Check the relevant adapter file in `servicer/builtin/ci_adapters`. The remaining variables may be specific to each service adapter, and will need to be configured in your CI environment, or defined in the `environment` section of `services.yaml`, or be provided locally in your `.servicer/.env.yaml` file.

#### CI Adapters ####
In order to standardize the environment Servicer runs in, a CI Adapter is used. Each CIAdapter is a python class that populates an instance variable called `env_map`, which contains key value pairs mapping environment variable names to their standardized Servicer equivalents.

Servicer provides default CI Adapters for your convenience. Please explore the `servicer/builtin/ci_adapters` directory to see what's available for each CI provider. In order to customize servicer to your needs, you can create your own CI Adapters in your project. By default, servicer will prefer CI Adapters found in the `.servicer/ci_adapters` directory of your project. See the Advanced Servicer Use Cases for more information on adapter overrides.

### Steps ###
Steps are sets of actions that share some configuration between services. For example, the 'deploy' step may only be executed when a Service Environment is present. Steps are declared project-wide in `services.yaml`. In the example below, several steps are defined.

```
...
steps:
  - name: build
  - name: test
  - name: deploy
    config:
      service_environment: '*'              # will only be executed within a service environment (based on environment mappings)
  - name: cleanup
    config:
      auxiliary: true                       # can only be explicitly executed (using the --step argument)
...
```
Steps are available for any service to implement. Given the above definition, during the first step, `build`, Servicer will look at every service and include its `build` step as a service-step in the complete dependency graph, if it exists. These service-steps will later be executed in the correct order.

Steps can be configured to be disregarded unless they are being run within an environment that matches one of the mappings defined in `environment` above. Given the environment defined above, any `deploy` service-steps will be disregarded unless Servicer is running in a matching Service Environment (any Service Environment will match the `'*'`). This syntax accepts glob and regex notations, and multiple matchers can be provided as a list. If there are multiple matchers, any match will allow execution of that particular service-step.

### Services ###
*Services* are abstract containers for pieces of your project. They can be a set of commands, or utilize a python module that wraps an integration with a 3rd party tool. Builtin service adapters automatically available through servicer are defined in `servicer/builtin/service_adapters`. You can also add your own service adapter within your project by adding it to your `.servicer/service_adapters` directory. However, you may decide to use Servicer as a command orchestrator, without leveraging any service adapters, and that is perfectly fine.

The service below builds a Docker image, and pushes/deploys it to the Google Container Registry.
```
...
services:
  my_docker_image:                     # User chosen name to uniquely identify this service
    providers:
      - gcloud                         # Initializes the given provider entry before running steps, useful for re-usable Auth
    service_type: gcloud/docker_image  # Optional, maps to the corresponding service adapter defined in servicer/builtin/service_adapters/
    steps:                             # Steps defined here must match a step defined in the `steps` list explained above
      build:
        config:
          # All config defined here is passed to the __init__ function of the corresponding service adapter.
          steps:
            - type: build
              args:
                image: demo-image
                dockerfile: Dockerfile
      deploy:
        commands:   # Commands are executed before the chosen service adapter is executed
          - docker login -u _json_key -p "$(cat /path/to/keyfile.json)" https://us.gcr.io/my-gcp-project
        config:
          # All config defined here is passed to the __init__ function of the corresponding service adapter.
          registry_path: my-gcp-project/this-project
          steps:
            - type: push
              args:
                image: demo-image
                tags:
                  - latest
...
```
The `providers` key is an optional key that allows you to specify one or more provider dependencies for the service. These entries should match the keys listed in the `providers` section of your `services.yaml`. For each entry here, servicer will ensure that the correct provider has been initialized before the steps for the service are executed.

Here is a service that builds a python package, and deploys it to Artifactory.
```
...
  my_python_package:
    service_type: package/pypi

    steps:
      build:
        commands:
          - rm -rf python_example/dist
          - python setup.py sdist
        config:
          package_info:
            package_file_path: setup.py
          # service adapter tasks map to functions available within the service adapter
          tasks:
            - type: read_package_info
      deploy:
        depends_on:
          - pypi-credentials:credentials

        config:
          package_info:
            package_file_path: setup.py
          tasks:
            - type: upload
              args:
                server: artifactory
                path: dist/*.tar.gz
...
```
Using `depends_on` gives you control over how Servicer's dependency graph is built. In the above example, Servicer will ensure that the `my_python_package:deploy` service-step is executed after the `pypi-credentials:credentials` service-step. The `my_python_packge:deploy` service-step also has an implicit dependency on the `my_python_packge:build` service-step, because the two service-steps belong to the same service, and the `build` step is defined before the `deploy` step in the steps list above.

A wildcard may also be provided in the place of a service name. For example, `*:test` means that the given service or service-step depends on the completion of all other `test` service-steps.

### Commands ###
Any service_type is able to execute arbitrary commands via the shell by using the `commands` key. You can avoid providing a `service_type` if all you want is a service wrapper for a set of commands. The `commands` key will execute commands before a service adapter config, while the `post_commands` key will execute commands after.

The `commands` list optionally accepts a raw string, or map containing a context providing more customization.
```
services:
  my-service:
    steps:
      build:
        commands:
          - docker build -f Dockerfile -t my-image .
      test:
        commands:
          - context:
              # interpolate all commands in this context using the given template
              template: '/bin/sh -c "%s"'
              # run all commands in this context in the provided docker context
              docker:
                image: my-image
                name: # defaults to a random string
                command: /bin/sh -c 'while sleep 5; do :; done'   # command to start the container with, sleep forever
                options:
                  env:
                    - MY_ENV_VAR
                  volume:
                    - $HOME/.ssh:/root/.ssh/
            commands:
              - echo 'Hi I'm running in a container!'
              - echo 'Me too!'

# final commands:
# docker run -d --env=MY_ENV_VAR --volume=$HOME/.ssh:/root/.ssh --name=H6GHGiXYjMwbAWEw my-image /bin/sh -c 'while sleep 5; do :; done'
# docker exec H6GHGiXYjMwbAWEw /bin/sh -c "echo 'Hi I'm running in a container!'"
# docker exec H6GHGiXYjMwbAWEw /bin/sh -c "echo 'Me too!'"
# docker stop H6GHGiXYjMwbAWEw
# docker rm H6GHGiXYjMwbAWEw
```

### Config File Management ###
Ultimately, Servicer runs with one compiled configuration file (this can be printed by running `servicer --show_config`). The heart of this is `services.yaml`. For convenience, `extends` and `includes` are two tools that can be used to merge other config files into `services.yaml`.

The `extends` key allows you to inherit from another YAML file. The structure of each file will be deep-merged, with values in the extending file overwriting values in the extended file. Lists are not merged, and will be completely overwritten.

In the example below, a file called `base.yaml` is essentially providing the top half of the `services.yaml` file.

```
# base.yaml

ci:
  providers:
    - bitbucket
  image: python:3.6.4

providers:
  aws:
    libraries:
      - awscli==1.15.49
      - boto3==1.7.48
  gcloud:
    auth_script: auth/gcloud.sh
    libraries:
      - google-api-python-client==1.6.5
```
```
# services.yaml

extends: base.yaml

services:
  postgres:
    provider: aws
    service_type: rds_instance

  api-django:
    docker: true
    depends_on:
      - postgres
    provider: gcloud
    service_type: kube_cluster
```
The includes key can also inherit from a different YAML file. However, unlike extends, values from the included file will overwrite values in the including file if there are key conflicts.

In the example below, kube-service.yaml includes configuration values for a service, and those values are being inherited by the api-django service.

```
# kube-service.yaml

docker: true
depends_on:
  - postgres
provider: gcloud
service_type: kube_cluster
```
```
# services.yaml

extends: base.yaml

services:
  api-django:
    includes: kube-service.yaml
```

An optional `params` key may be used for interpolation, allowing for re-usable, generic config files. The example below is equivalent to the example above.

```
# kube-service.yaml

docker: true
depends_on:
  - ${db}
provider: ${provider}
service_type: kube_cluster
```
```
# services.yaml

extends: base.yaml

services:
  api-django:
    includes:
      path: kube-service.yaml
      params:
        db: postres
        provider: gcloud
```

### Variable Interpolation ###
All configuration files support variable interpolation using the `${MY_VAR}` format.
To pull from an environment variable, use `${MY_ENV_VAR}`.
To fall back to a default value if the chosen environment variable does not exist, use `${MY_ENV_VAR:"my-default-value"}`

## Testing the Job ##
To make it easy to test deployments in your local environment, servicer will automatically read from an `.env.yaml` file in your servicer configuration directory, if it exists. It is recommended to add this file to your `.gitignore`, as it is only intended to be used for local development and manual environment creation.

Example:
```
# .servicer/.env.yaml
AWS_DEFAULT_REGION: us-east-2
BRANCH: env-test
BUILD_NUMBER: '0001'
DATABASE_NAME: my_db
DATABASE_USERNAME: postgres
DATABASE_PASSWORD: xxxxxxxx
GCLOUD_KEY_FILE_PATH: /Users/me/my_gcloud_credentials.json
GCLOUD_REGION: us-central1
GCLOUD_ZONE: us-central1-f
PROJECT_NAME: my-project
SERVICE_ENVIRONMENT: test
```

`.env.yaml` can also be defined at `~/.servicer/.env.yaml` to support multi-project defaults. Values in the project level `.env.yaml` will take precedence over values in your user folder.

## Git Integration ##
Servicer provides a few handy Git integrations to optimize jobs. By default, git integration is disabled. To enable it, set `git: enabled: true`.

### Change Detection ###
Servicer can use a `git diff` to determine which services in your project are different between the current commit and either the commit associated with its last successful job, or one passed to Servicer by an environment variable. This second commit is Servicer's _reference point_, and the list presented by `git diff` provides Servicer its change detection.

By default, Servicer will maintain its own set of git tags that identify commits it should use as reference points. The format of these tags is `servicer-<BRANCH>-<BUILD_DATE>-<BUILD_NUMBER>`. Servicer relies upon the CI framework it is working on (like Jenkins) to provide the `BRANCH` and `BUILD_NUMBER` variables. Alternatively, the `GIT_DIFF_REF` environment variable can be set manually.

Servicer will use the first reference point it can find, and attempts to find it in this order:
1. The `GIT_DIFF_REF` environment variable, if it’s set and is a valid commit.
2. The latest servicer git tag matching the current branch, if `git: diff-tagging-enabled: true`.
3. The latest servicer git tag matching any branch, if `git: diff-defaults-to-latest-tag: true`.

Servicer will also attempt to remove any stale tags automatically. Tags present only on deleted branches, or tags that are no longer the latest tag for a branch will be removed.

### Skipping Steps for Unchanged Services ###
When using Git integration, Servicer can skip steps for the services that haven't changed (unless those steps are explicit dependencies). Here is an example of configuring this.

```
git:
  enabled: true
  config:
    user.name: servicer   # The name Servicer will use when committing to the repo.
  ignore-unchanged: true  # Determine whether to skip unchanged services or not.
  ignore_paths:           # When running git diff, Servicer will ignore files that are matched by
    - *README.md          # values in this array.

services:
  my_python_package:      # Name shared by this service and the relevant directory within the repo.
    provider: pypi
    service_type: pypi

    git:
      watch_paths:              # When running git diff, Servicer will consider this service changed if
        - my_python_package/*   # any non-ignored paths returned are matched by any value in this array.
    steps:
      build:
        commands:
          - echo 'I must have changed!'
```
In this case, Servicer will only execute `my_python_package`'s steps (only `build` is present) if any file within the my_python_package directory, except README.md, was returned by Servicer's `git diff`.

Supported formats for `watch_paths` and `ignore_paths` are simple text with `*` as a wildcard, and full regexes in the format `/.*/`.

### Automatic Versioning ###
_*Warning:* This is an experimental feature. Automatic versioning requires Servicer to make automated commits back to your repository with updated version numbers for package services. This can have unintended side effects with your CI solution unless "you know what you're doing"._

As part of git integration, Servicer can automatically increase the version number of the packages it manages and commit the new version numbers to the repository. When Servicer is being run on a CI pipeline, `ignore-servicer-commits` can be set to true to have servicer inspect the commit authors, and self-terminate if the job was initiated in response to a commit made by Servicer.

Below is an example of a PyPi service that inherits from the Package Service Adapter and implements autoversioning.
```
steps:
  build:
    config:
      package_file_path: ${package_directory}/setup.py
      steps:
        - type: set_auto_version
    post_commands:
      - rm -rf ${package_directory}/dist
      - python3 ${package_directory}/setup.py sdist --dist-dir=${package_directory}/dist
  deploy:
    config:
      package_file_path: ${package_directory}/setup.py
      steps:
        - type: upload
          args:
            server: artifactory
            path: ${package_directory}/dist/*.tar.gz
        - config:
          steps:
            - type: commit_and_push_changes
```

### Environment Destruction ###
Because every environment setup is unique, environment destruction is not automated. However, by configuring the `destroy` step for services, you can condense the complete destruction of a service environment into a single command:

`SERVICE_ENVIRONMENT=my-env servicer --destroy`

Example kubernetes destroy configuration, assuming your services exist within a kubernetes namespace that matches your service_environment name:
```
services:
  kubernetes:
    destroy:
      commands:
        - kubectl delete ns ${SERVICE_ENVIRONMENT}
```
The `destroy` step is a magic step that does not need to be defined in your `.servicer/services.yaml`.

## Advanced Servicer Use Cases ##
Servicer's core interface with external CI's, cloud provider APIs, etc, exists as a collection of python modules called Adapters. These Adapters can be found in the `builtin` directory of the project, and may be overridden or extended if they do not meet your needs.

To override an Adapter, simply mirror the directory structure of `builtin` directly inside your `.servicer` folder.
```
.servicer/
  service_adapters/
    aws/
      rds_instance.py  # this overrides servicer's builtin rds_instance adapter
      custom_task_service.py
  services.yaml
```
`custom_task_service.py` can also inherit from servicer's `builtin` adapter classes, and selectively override just the functionality that isn't working for you.

```
#custom_adapter.py

from servicer.builtin.service_adapters.task_service import Service as BaseService

class Service(BaseService):
    # overrides task_service.Service's up() method, but still calls it
    def up(self):
        super().up()

        print('my custom logic here!')

    def foo(self):
        print('bar')

```

Then you can utilize your custom service adapters like you normally would with builtin adapters:

```
services:
  my-service:
    service_type: aws/custom_task_service
```
