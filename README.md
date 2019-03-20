# Servicer #

Servicer is a configuration-based CI automation framework that runs inside popular CI platforms, such as Bitbucket Pipelines, Jenkins, and CircleCI.

Core Features:
* Run and debug your CI jobs locally.
* Map your branches to independent service environments, allowing you to use the same process to deploy production, testing, and development environments.
* Configure intelligent Change Detection, to only build the services and dependencies you need for the changes made (great for monorepos!).

Servicer uses the *services* and *steps* you define in `.servicer/services.yaml`. A servicer execution will roughly do the following:
1. Normalize the current CI environment (by standardizing environment variables).
2. Construct the complete servicer configuration (interpolating dynamic value tokens).
3. Determine which services can be ignored by Change Detection.
4. Build a dependency graph of remaining service-steps.
5. Execute each service-step in the order determined by the dependency graph.

## Separation of Concerns ##
Servicer is separated into three main components: adapters, services, and the project environment.

*Adapters* allow Servicer to use or interact with external systems, like Google Cloud Platform, GitHub, and Jenkins. Three kinds of adapters exist: CI adapters, auth adapters, and service adapters. These are written as reusable python modules, and are located in `servicer/builtin`.

 *Services* are the building blocks of your project. Services are defined in the `.servicer/services.yaml` file in your project, and these definitions include the configuration and commands needed to build, test and deploy each service. Additionally, dependencies may be defined to automate the order services and steps are executed in.

The *project environment* should contain environment variables for holding credentials and other secrets that should not be committed to source control. These can be configured on your CI tool, or, if you are running Servicer locally, from a `.servicer/*.env.yaml` file.

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
These commands can be run locally or in the context of a CI job.

By default, all service-step dependencies will also be executed. If you will like to disable this behavior, use the `--ignore_dependencies` flag.

If you would like to execute a test run of servicer without actually executing any service-steps, you can add the `--dry` flag.

To set the desired logging level (debug, info, warn, error), use the `--log_level` flag.

For a complete list of flags and options that can be provided to the `servicer` command, please see `servicer --help`.

## Configuration ##
`.servicer/services.yaml` must be present at the root of your project. `servicer/builtin/defaults.yaml` (https://github.com/wmgroot/servicer/blob/master/servicer/builtin/defaults.yaml) contains default values and descriptions of the values you can provide in `.servicer/services.yaml`.

Within this *Configuration* section of the README, consider each of these subsections to compose the `services.yaml` on one project.

### Environment ###
The `environment` section of `services.yaml` will let you define environment variables that you're ok with existing in source control. Additionally, you can control the branch -> service_environment settings, allowing you to change the defaults. Consider the example below.

```
environment:
  # In this example, SERVICE_ENVIRONMENT will be `production` if the branch is `master`.
  # SERVICE_ENVIRONMENT will be `develop` if the branch is `develop`.
  # Otherwise, if the branch matches `env-*`, SERVICE_ENVIRONMENT will be the sanitized branch name.
  mappings:
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
Servicer requires several environment variables to be configured which control the parameters of each service. Some of these environment variables will be automatically pulled from your CI environment and standardized by the CI Adapter it is using. Check the relevant adapter file in `servicer/builtin/ci_adapters`. The remaining variables may be specific to each service adapter, and will need to be configured in your CI environment, or defined in the `environment` section of `services.yaml`.

#### CI Adapters ####
In order to standardize the environment Servicer runs in, a CI Adapter is used. Each CIAdapter is a python class that populates an instance variable called `env_map`, which contains key value pairs mapping environment variable names to their standardized Servicer equivalents.

Servicer provides default CI Adapters for your convenience. Please explore the `servicer/builtin/ci_adapters` directory to see what's available for each CI provider. In order to customize servicer to your needs, you can create your own CI Adapters in your project. By default, servicer will prefer CI Adapters found in the `.servicer/ci_adapters` directory of your project. See the Advanced Servicer Use Cases for more information on adapter overrides.

### Steps ###
_Steps_ are actions that Servicer will execute to accomplish its work on the services. Steps are declared project-wide in `services.yaml`. In the example below, several steps are defined.

```
...
steps:
  - name: credentials
  - name: build
  - name: unit_test
  - name: integration_test
  - name: deploy
      config:
        requires_service_environment: true
...
```
The execution of steps is done at a project-wide scale. Given the above definition, during the first step, `credentials`, Servicer will look at every service and execute its `credentials` step, if one is provided. When the `credentials` step is complete, Servicer will being the `build` step, look at every service, and execute its `build` step, if one is provided. Servicer continues doing this until all of the `steps` have been completed.

Steps can be configured to be disregarded unless they are being run within an environment that matches one of the mappings defined in `environment` above. Given the environment defined above, `deploy` will be disregarded unless Servicer is running on the `master`, `develop`, or a `env-*` branch.

### Services ###
*Services* are things that Servicer should handle, like portions of your project or pieces of third party software that your CI pipeline needs to work with. Servicer uses *service adapters* to work with these various services. Builtin service adapters automatically available through servicer are defined in `servicer/builtin/service_adapters`. You can also add your own service adapter within your project by adding it to your `.servicer/service_adapters` directory.

The service below builds a Docker image, and pushes/deploys it to the Google Container Registry.
```
...
services:
  my_docker_image:              # User chosen name to identify this service
    providers:
      - gcloud                  # Initializes the given provider entry before running steps
    service_type: gcloud/docker_image  # Maps to the corresponding service adapter defined in servicer/builtin/service_adapters/
    steps:                      # Steps defined here must match a step defined in the `steps` list discussed above
      build:
        config:
          # All config defined here is passed to the __init__ function of the corresponding service adapter.
          steps:
            - type: build
              args:
                image: demo-image
                dockerfile: Dockerfile
      deploy:
        commands:
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
    depends_on:
      - artifactory-pypi
      - pypi-credentials
    steps:
      build:
        commands:    # These are standard shell commands Servicer will execute
          - rm -rf python_example/dist
          - python setup.py sdist
        config:
          # The service adapter handles things nested at this level and deeper
          package_info:
            package_file_path: setup.py
          steps:
            - type: read_package_info
      deploy:
          config:
            package_info:
              package_file_path: setup.py
            steps:
              - type: upload
                args:
                  server: artifactory
                  path: dist/*.tar.gz
...
```
Using `depends_on` defines the other services your service depends on. Servicer will execute the dependee's matching step before executing the dependor's current step. In this case, Servicer will first execute the build steps for the `artifactory-pypi` and `pypi-credentials` services, which were created by the user and are not included here, before executing the `build` step for `my_python_package`.

The `depends_on` key may also be used at the step level of your configuration. Below you can see that the `deploy` step for our `api-django` service contains a dependency on `postgres:deploy`. Servicer will ensure that the service-step `api-django:deploy` is executed after the service-step `postgres:deploy`.

A wildcard may also be provided in the place of a service name. For example, `*:test`. This means that the given service or service-step depends on the completion of all other services' `test` step.
```
...
  postgres:
    provider: aws
    service_type: rds_instance

    steps:
      deploy:
        config:
          rds_params:
            AllocatedStorage: 256
            DBInstanceClass: db.m4.large
            DBInstanceIdentifier: ${PROJECT_NAME}-${SERVICE_ENVIRONMENT}
            DBName: ${DATABASE_NAME}
            Engine: postgres
            MasterUsername: ${DATABASE_USERNAME}
            MasterUserPassword: ${DATABASE_PASSWORD}
            PubliclyAccessible: true
            StorageEncrypted: true
            StorageType: gp2 # General purpose SSD
            Tags:
              - Key: project
                Value: ${PROJECT_NAME}
            VpcSecurityGroupIds:
              - sg-12345678 # default

  api-django:
    docker: true
    provider: gcloud
    service_type: kube_cluster

    steps:
      build:
        commands:
          - docker build . -t ${PROJECT_NAME}-api
      deploy:
        depends_on:
          - postgres:deploy
        commands:
          - ./util/install-docker-compose.sh
        config:
          cluster_name: my_gke_cluster
          project: my_gcloud_project
          compute_zone: us-central1-f
          wait_for_pending: true
          cluster_configs:
            - ...    # kubernetes config goes here
```
This concludes the single, long `services.yaml` example above.

### Config File Management ###
Ultimately, Servicer runs with one configuration file that is printed each time it runs. The heart of this is `services.yaml`. For convenience, `extends` and `includes` are two tools that can be used to merge other config files into `services.yaml`.

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

An optional `params` key may be used for interpolation, allowing for more generic config files. The example below is equivalent to the example above.

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
Servicer provides a few handy Git integrations to optimize jobs. By default, git integration is disabled. To enable it, set `git: enabled` to `true`.

### Change Detection ###
Servicer can run `git diff` to determine which services in your project are different between the current commit and either the commit associated with its last successful job, or one passed to Servicer by an environment variable. This second commit is Servicer's _reference point_, and the list presented by `git diff` provides Servicer its change detection.

By default, Servicer will maintain its own set of git tags that identify commits it should use as reference points. The format of these tags is `servicer-<BRANCH>-<BUILD_DATE>-<BUILD_NUMBER>`. Servicer relies upon the CI framework it is working on (like Jenkins) to provide the `BRANCH` and `BUILD_NUMBER` variables. Alternatively, the `GIT_DIFF_REF` environment variable can be set manually.

Servicer will use the first reference point it can find, and attempts to find it in this order:
1. The `GIT_DIFF_REF` environment variable, if it’s set and is a valid commit.
2. The latest servicer git tag matching the current branch, if `git: diff-tagging-enabled` is `true`.
3. The latest servicer git tag matching any branch, if `git: diff-defaults-to-latest-tag` is `true`.

### Skipping Steps for Unchanged Services ###
When using Git integration, Servicer can skip steps for the services that haven't changed except those steps which are dependees. An example of how to employ this is below.

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
_*Warning:* This is an experimental feature. Automatic versioning requires Servicer to make automated commits back to your repository with updated version numbers for package services. This can have unintended side effects with your CI solution unless you know what you're doing._

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
