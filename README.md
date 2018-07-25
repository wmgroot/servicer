# Servicer
CI/CD Automation Framework

The primary goal of this framework is to completely automate creating, updating, and removing an environment (a collection of services). To accomplish this, this framework executes in your CI environment (eg: Bitbucket Pipelines, Gitlab, Jenkins, CircleCI, etc) and interfaces directly with cloud infrastructure provider libraries (AWS, Google Cloud, Azure, etc).

## Separation of Concerns ##
Servicer is separated into 3 main components:

### Adapters ###
CI Adapters, Auth Adapters, and Service Adapters are written as re-usable python modules. These modules do not carry any project specific concepts, and are designed to be an extendable, re-usable framework for interfacing with any cloud service provider.

### Project Service Configuration ###
Your project's `services.yaml` file represents the settings and service relationships unique to your project. This configuration resides in source control.

### Environment Settings ###
Any environment specific credentials or secrets should live in simple environment variables, which can be read and inserted into the build at build-time. These secrets should never be checked into source control, and instead be populated in the build environment.

## services.yaml ##
The services config file supports environment variable substitution using the `${MY_VAR}` format.

Example config file for a deploying an AWS RDS instance and GCloud Kubernetes cluster from Bitbucket Pipelines CI:
```
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

services:
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
    depends_on:
      - postgres
    provider: gcloud
    service_type: kube_cluster

    steps:
      build:
        commands:
          - docker build . -t ${PROJECT_NAME}-api
      test:
        commands:
          - ./util/install-docker-compose.sh
          - docker-compose -f docker-compose-test.yml up --abort-on-container-exit
```

### Extends ###
The key `extends` can be used to inherit values from another servicer config file.
Keys and values between the two config files will be merged, with values from the extending file taking precedence.

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

### Includes ###
The key `includes` can also be used to inherit values from another servicer config file.

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

An optional `params` key may be provided to provide interpolation tokens. This is equivalent to the example above.

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

### Environment ###
The `environment` section of `services.yaml` will let you define environment variables that you're ok with existing in source control. Additionally, you can control the branch -> service_environment settings, allowing you to change the defaults.
```
environment:
  # branch -> service_environment mappings
  # if the branch is 'master', SERVICE_ENVIRONMENT will be 'production'
  # if any branch is matched, any steps requiring a service_environment will be executed
  mappings:
    - branch: master
      environment: production
    - branch: develop
    - branch: env-*

  # define environment variables here (do not define secrets)
  variables:
    FOO: BAR
    PROJECT_NAME: ${PRE_DEFINED_ENV_VAR}-plus-some
```

### Git Integration ###
Servicer provides a few handy Git integrations to facilitate your build process. By default, git integration is globally disabled, simply change `enabled` to true in your `services.yaml` to enable it.

```
git:
  enabled: false
  config:
    user.name: servicer
  default-branch: master
  ignore-unchanged: true
  ignore-servicer-commits: false
```

#### Selective Builds ####
For each service, you can optionally specify paths in your project that should trigger servicer to build, test, or deploy that service. Use `watch_paths` and `ignore_paths` to specify which files to match. Supported formats are simple text with `*` as a wildcard, or full regexes in the format `/.*/`. If no `watch_paths` or `ignore_paths` are provided, the service will be built every time.

For example, this pypi service will only build, test, or deploy when a file inside project folder `servicer` is changed.
However, if `servicer/README.md` changes, the pypi service will still not build, test, or deploy, because `*README.md` is ignored at the project level.
```
git:
  ignore_paths:
    - *README.md

services:
  pypi:
    provider: pypi
    service_type: pypi

    git:
      watch_paths:
        - servicer/*
```

#### Automatic Versioning ####
*Warning:* This is an experimental feature. Automatic versioning requires Servicer to make automated commits back to your repository with updated version numbers for package services. This can have unintended side effects with your CI solution unless you know what you're doing.

Git integration must also be enabled.
`ignore-servicer-commits` can also be set to true to have servicer inspect the commit authors, and self-terminate if it detects a build started by its own automated commit.

For a Service Adapter that inherits from the Package Service Adapter (for example this PyPI service):
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
              args:
                protocol: https
```

## Environment ##
The framework requires several environment variables to be configured which control the parameters of each service. Some of these environment variables will be automatically pulled from your CI environment, and converted using a CI Adapter. The remaining variables may be specific to each service adapter, and will need to be configured in your CI environment, or defined in the `environment` section of `services.yaml`.

To make it easy to test deployments in your local environment, servicer will automatically read from an `.env.yaml` file in your servicer configuration directory, if it exists. It is recommended to add this file to your `.gitignore`, as it is only intended to be used for local development and manual environment creation.

Example:
```
# build/.env.yaml
AWS_DEFAULT_REGION: us-east-2
BRANCH: env-test
BUILD_NUMBER: '0001'
DATABASE_NAME: my_db
DATABASE_USERNAME: postgres
DATABASE_PASSWORD: XXX
GCLOUD_KEY_FILE_PATH: /Users/me/my_gcloud_credentials.json
GCLOUD_COMPUTE_REGION: us-central1
GCLOUD_COMPUTE_ZONE: us-central1-f
PROJECT_NAME: my-project
SERVICE_ENVIRONMENT: test
```

## Usage ##
For the simplest use case of Servicer, simply add this command to your CI workflow, and each of your services will be deployed each time your CI workflow runs.
```
servicer
```
This will execute all steps for all services present in `services.yaml`.

```
servicer --service=foo
```
This will execute all steps for only the service called `foo`.

```
servicer --step=build,test
```
This will execute the `build` and `test` steps for all services.

## Advanced Use Cases ##
Servicer's core interface with external CI's, cloud provider APIs, etc, exists as a collection of python modules called Adapters. These Adapters can be found in the `builtin` directory of the project, and may be overridden or extended if they do not meet your needs.

To override an Adapter, simply mirror the directory structure of `builtin` directly inside your `.servicer` folder.
```
.servicer
  __init__.py
  service_adapters
    __init__.py
    aws
      __init__.py
      rds_instance.py  # this overrides servicer's builtin rds_instance adapter
      new_adapter.py
  services.yaml
```
`new_adapter.py` can also inherit from servicer's builtin adapter classes, and selectively override just the functionality that isn't working for you.

### Service Adapters ###
The fundamental building block of Servicer is a service. In order to create and destroy these services, servicer uses Service Adapters, which provide an interface between Servicer and each cloud provider's API or library. These Service Adapters can be either a python class called `Service` with `up` and `down` methods, or a shell script with `up` and `down` functions.

The `up` method is responsible for both creating and updating the service. Similarly, the `down` method is responsible for tearing down and removing the service. For this framework to function as expected, both methods *must* be *idempotent*.

Servicer provides default Service Adapters for your convenience. Please explore the `builtin/service_adapters` directory to see what's available for each cloud provider. In order to customize servicer to your needs, you can create your own Service Adapters in your project. By default, servicer will prefer service adapters found in the `.servicer/service_adapters` directory of your project.

### CI Adapters ###
In order to standardize the environment Servicer runs in, a CI Adapter is used. Each CIAdapter is a python class that populates an instance variable called `env_map`, which contains key value pairs mapping environment variable names to their standardized Servicer equivalents.

Servicer provides default CI Adapters for your convenience. Please explore the `builtin/ci_adapters` directory to see what's available for each CI provider. In order to customize servicer to your needs, you can create your own CI Adapters in your project. By default, servicer will prefer CI Adapters found in the `.servicer/ci_adapters` directory of your project.
