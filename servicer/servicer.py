import os
import sys
import importlib
import pkg_resources
import json
import argparse
import yaml
import re
import copy
from datetime import datetime

from .config_loader import ConfigLoader
from .dependency_grapher import DependencyGrapher
from .git import Git
from .run import run
from .token_interpolator import TokenInterpolator
from .logger import Logger

class Servicer():
    def __init__(self, args=None, init=True):
        if not init:
            return

        self.datetime = datetime

        self.version = pkg_resources.get_distribution('servicer').version
        self.run = run

        if args == None:
            args = vars(self.load_arguments())

        logger_params = {
            'level': args['log_level']
        }
        if os.getenv('DEBUG'):
            logger_params['level'] = 'debug'
        self.logger = Logger(**logger_params)

        self.token_interpolator = TokenInterpolator(logger=self.logger)

        if 'version' in args and args['version']:
            self.logger.log(self.version)
            sys.exit(0)

        self.logger.log('servicer version: %s' % self.version)

        self.load_environment(args)

        self.config_loader = ConfigLoader(args, logger=self.logger)
        self.config = self.config_loader.load_config()
        self.active_services = None

        self.normalize_ci_environment()
        self.determine_service_environment()

        self.config_loader.interpolate_config(self.config)

        self.logger.log('Services Config:', level='debug')
        self.logger.log(json.dumps(self.config, indent=4, sort_keys=True, default=str), level='debug')

        if 'show_config' in self.config['args'] and self.config['args']['show_config']:
            self.logger.log('Services Config:')
            self.logger.log(json.dumps(self.config, indent=4, sort_keys=True, default=str))
            sys.exit(0)

        self.git_init()

        self.decide_service_step_order()

    def decide_service_step_order(self):
        self.load_steps()

        if not self.active_services:
            self.active_services = self.load_service_modules()

        self.dependency_grapher = DependencyGrapher(
            self.config,
            self.active_services,
            self.steps,
            self.step_order,
            self.active_steps,
            logger=self.logger,
        )
        self.service_step_order = self.dependency_grapher.order_service_steps(self.active_services)

    def load_arguments(self):
        parser = argparse.ArgumentParser(description='Process deployment options.')

        parser.add_argument('-g', '--generate_ci', action='store_true', help='generate a ci config file, do not run any deploy options')
        parser.add_argument('-s', '--service', help='deploy only the provided service')
        parser.add_argument('-f', '--services_file', default='services.yaml', help='custom path to your services config file (default is services.yaml)')
        parser.add_argument('-p', '--servicer_config_path', default='%s/.servicer' % os.getcwd(), help='path to your servicer directory (default is ./servicer)')
        parser.add_argument('--env_file_paths', default='%s/.servicer/.env.yaml:%s/.servicer/.env.yaml' % (os.getenv('HOME'), os.getcwd()), help='paths to your local .env files, colon-separated')
        parser.add_argument('--step', help='perform the comma-separated build steps, defaults to all steps')
        parser.add_argument('-c', '--show_config', action='store_true', help='prints the interpolated config file')
        parser.add_argument('-u', '--no_ignore_unchanged', '--no_cd', action='store_true', help='disables ignoring services through change detection')
        parser.add_argument('--no_tag', action='store_true', help='disables build tagging')
        parser.add_argument('--no_auth', action='store_true', help='disables build authentication, useful if you are already authenticated locally')
        parser.add_argument('-d', '--ignore_dependencies', action='store_true', help='disables automatic dependency execution')
        parser.add_argument('--tag', action='store_true', help='generate a git tag')
        parser.add_argument('-v', '--version', action='store_true', help='display the package version')
        parser.add_argument('-x', '--destroy', action='store_true', help='destroy the current service environment')
        parser.add_argument('--dry', action='store_true', help='skip all service-step actions')
        parser.add_argument('--log_level', default='info', help='set the desired logging level, options are: [info,debug,warn,error]')

        return parser.parse_args()

    def load_environment(self, args):
        os.environ['PROJECT_PATH'] = os.environ['PWD']
        os.environ['BUILD_DATETIME'] = str(self.datetime.utcnow())
        os.environ['BUILD_DATE'] = self.datetime.now().strftime('%Y-%m-%d')

        if 'env_file_paths' not in args:
            return

        for path in args['env_file_paths'].split(':'):
            self.load_env_file(path)

    def load_env_file(self, path):
        self.logger.log('checking for (.env.yaml) at (%s)' % path)
        if os.path.exists(path):
            self.logger.log('(.env.yaml) found, including these arguments:')

            yaml_dict = yaml.load(open(path))
            for key, value in yaml_dict.items():
                os.environ[key] = value
                self.logger.log(key)
            self.logger.log()

    def normalize_ci_environment(self):
        if 'ci' not in self.config:
            return

        self.print_title('normalizing CI environment')

        self.config['ci']['adapters'] = {}
        for p in self.config['ci']['providers']:
            self.logger.log('CI Adapter: %s' % p)
            ci_adapter_modules = [
                {
                    'name': 'ci_adapters.%s' % p,
                    'package': 'ci_adapters',
                    'file_path': '%s/ci_adapters/%s.py' % (self.config['config_path'], p),
                },
                {
                    'name': 'servicer.builtin.ci_adapters.%s' % p,
                    'package': 'servicer.builtin.ci_adapters',
                    'file_path': '%s/builtin/ci_adapters/%s.py' % (self.config['module_path'], p),
                },
            ]
            module = self.load_module_from_paths(ci_adapter_modules)
            self.config['ci']['adapters'][p] = module.CIAdapter(logger=self.logger)

        if 'generate_ci' in self.config['args'] and self.config['args']['generate_ci']:
            for ci_adapter in self.config['ci']['adapters'].values():
                self.active_services = self.config['services'].keys()
                self.decide_service_step_order()

                ci_adapter.generate_ci_config(self.config, self.service_step_order)
            sys.exit(0)

        for ci_adapter in self.config['ci']['adapters'].values():
            ci_adapter.convert_environment_variables()

    def determine_service_environment(self):
        self.logger.log()
        self.service_environment = os.getenv('SERVICE_ENVIRONMENT') or self.get_service_environment(os.getenv('BRANCH', 'local'))

        self.logger.log('branch: %s' % os.getenv('BRANCH'))
        self.logger.log('service environment: %s' % self.service_environment)
        if self.service_environment:
            os.environ['SERVICE_ENVIRONMENT'] = self.service_environment

    def get_service_environment(self, branch):
        service_environment = None
        if 'environment' not in self.config or 'mappings' not in self.config['environment']:
            return service_environment

        mappings = self.config['environment']['mappings']
        service_environment, self.service_environment_config = self.map_service_environment(branch, mappings)

        if service_environment:
            formatter = self.config['environment'].get('formatter')
            if formatter:
                if 'replace' in formatter:
                    for replacer in formatter['replace']:
                        for f in replacer['from']:
                            if f in service_environment:
                                service_environment = service_environment.replace(f, replacer['to'])

                if formatter.get('uppercase'):
                    service_environment = service_environment.upper()
                if formatter.get('lowercase'):
                    service_environment = service_environment.lower()

                truncate = formatter.get('truncate')
                if truncate:
                    service_environment = service_environment[:truncate]

            if 'variables' in self.service_environment_config:
                self.config_loader.load_environment_variables(self.service_environment_config['variables'])

        return service_environment

    def map_service_environment(self, branch, mappings=[]):
        for m in mappings:
            if 'branch' in m:
                if m['branch'].startswith('/') and m['branch'].endswith('/'):
                    regex = m['branch'][1:-1]
                else:
                    regex = '^%s$' % m['branch'].replace('*', '.*')

                result = re.match(regex, branch)
                if result:
                    return m.get('environment', branch), m
            elif 'tag' in m:
                # TODO: support tag mapping
                pass

        return None, None

    def git_init(self):
        if not 'git' in self.config or not self.config['git']['enabled']:
            return

        self.print_title('initializing git integration')

        git_args = { 'hide_output': 'DEBUG' not in os.environ, 'logger': self.logger }
        if 'protocol' in self.config['git']:
            git_args['protocol'] = self.config['git']['protocol']
        self.git = Git(**git_args)
        self.git.config = self.config['git']

        if 'auto-set-branch' in self.config['git'] and self.config['git']['auto-set-branch']:
            if 'BRANCH' not in os.environ:
                os.environ['BRANCH'] = self.git.current_branch()

        if 'auto-set-commit' in self.config['git'] and self.config['git']['auto-set-commit']:
            if 'COMMIT_SHORT' not in os.environ:
                os.environ['COMMIT_SHORT'] = self.git.current_commit(min_length=self.config['git']['commit-min-length'])
            if 'COMMIT_LONG' not in os.environ:
                os.environ['COMMIT_LONG'] = self.git.current_commit()
            if 'COMMIT' not in os.environ:
                os.environ['COMMIT'] = os.environ['COMMIT_SHORT']

        if 'config' in self.config['git']:
            for key, value in self.config['git']['config'].items():
                result = self.run('git config %s' % key, check=False)['stdout'].strip()
                if result == '':
                    self.run('git config %s "%s"' % (key, value))

        if 'fetch-all' in self.config['git'] and self.config['git']['fetch-all']:
            self.run('git fetch')
        elif 'fetch-tags' in self.config['git'] and self.config['git']['fetch-tags']:
            self.run('git fetch --tags')

        if 'tag' in self.config['args'] and self.config['args']['tag']:
            self.tag_build(check_git=False)
            sys.exit(0)

        if 'GIT_DIFF_REF' in os.environ:
            result = self.run('git cat-file -t %s' % os.environ['GIT_DIFF_REF'], check=False)
            if result['status'] != 0:
                self.logger.log('Invalid GIT_DIFF_REF provided!')
            else:
                self.config['git']['diff-ref'] = os.environ['GIT_DIFF_REF']

        if 'BRANCH' in os.environ:
            if self.config['git']['diff-tagging-enabled'] and 'diff-ref' not in self.config['git']:
                servicer_tag_part = 'servicer-%s' % self.git.sanitize_tag(os.environ['BRANCH'])
                self.build_tags = [t for t in self.git.list_tags() if t.startswith(servicer_tag_part)]

                self.logger.log('branch tag: %s' % servicer_tag_part, level='debug')
                self.logger.log('matching tags:', level='debug')
                self.logger.log('\n'.join(self.build_tags), level='debug')

                if len(self.build_tags) > 0:
                    self.config['git']['diff-ref'] = self.build_tags[-1]

            if 'diff-defaults-to-latest-tag' in self.config['git'] and self.config['git']['diff-defaults-to-latest-tag'] and 'diff-ref' not in self.config['git']:
                result = self.run('git describe --tags --abbrev=0 --match "servicer-*" HEAD', check=False)

                if result['status'] == 0:
                    latest_tag = result['stdout'].strip()
                    if latest_tag:
                        self.logger.log('defaulting to latest servicer git tag')
                        self.config['git']['diff-ref'] = latest_tag

            # TODO: remove this feature in next breaking update
            if 'default-branch' in self.config['git'] and self.config['git']['default-branch'] and 'diff-ref' not in self.config['git']:
                if os.environ['BRANCH'] != self.config['git']['default-branch']:
                    self.logger.log('defaulting Git Diff Ref to default-branch')
                    self.config['git']['diff-ref'] = 'origin/%s' % self.config['git']['default-branch']

        if 'diff-ref' in self.config['git']:
            self.logger.log('Git Diff Ref: %s\n' % self.config['git']['diff-ref'])

        if self.config['git']['ignore-servicer-commits'] and 'diff-ref' in self.config['git']:
            authors = self.git.authors_for_changes_ahead_of_ref(self.config['git']['diff-ref'])
            self.logger.log('Commit authors: %s' % authors)
            if 'servicer' in authors:
                self.logger.log('Automated servicer changes were detected, skipping this build.')
                sys.exit(0)

    def tag_build(self, check_git=True):
        if check_git:
            if not 'git' in self.config or not self.config['git']['enabled']:
                return

            if not self.config['git']['auto-tag'] or 'BUILD_NUMBER' not in os.environ:
                return

            if 'no_tag' in self.config['args'] and self.config['args']['no_tag']:
                return

        self.remove_stale_tags()
        servicer_tag = self.servicer_git_tag()

        if servicer_tag:
            self.logger.log('Tagging: %s' % servicer_tag)
            self.git.tag(servicer_tag, push=True)

    def remove_stale_tags(self):
        self.logger.log('Removing old tags...')

        build_tags = [t for t in self.git.list_tags() if t.startswith('servicer-')]
        self.logger.log('\nexisting servicer tags:', level='debug')
        self.logger.log('\n'.join(build_tags), level='debug')

        branches = ['/'.join(b.split('/')[1:]) for b in self.git.list_remote_branches()]
        tag_prefixes = [self.git.sanitize_tag(b) for b in branches]
        self.logger.log('\nexisting branch tag prefixes:', level='debug')
        self.logger.log('\n'.join(tag_prefixes), level='debug')

        valid_tags = set()
        for tp in tag_prefixes:
            prefix = 'servicer-%s' % tp
            for bt in build_tags:
                if bt.startswith(prefix):
                    valid_tags.add(bt)

        tags_to_delete = list(set(build_tags) - valid_tags)
        self.logger.log('\nstale tags for other branches:', level='debug')
        self.logger.log('\n'.join(tags_to_delete), level='debug')

        self.git.delete_tag(tags_to_delete)

        tag_prefix = self.git.sanitize_tag(os.environ['BRANCH'])
        build_tags_for_branch = [bt for bt in build_tags if bt.startswith('servicer-%s' % tag_prefix)]

        self.logger.log('\nstale tags for this branch: %s' % tag_prefix, level='debug')
        self.logger.log('\n'.join(build_tags_for_branch), level='debug')
        self.git.delete_tag(build_tags_for_branch)

    def servicer_git_tag(self):
        if 'BRANCH' not in os.environ:
            return

        sanitized_tag = self.git.sanitize_tag(os.environ['BRANCH'])
        return 'servicer-%s-%s-%s' % (sanitized_tag, os.environ['BUILD_DATE'], os.environ['BUILD_NUMBER'])

    def load_service_modules(self):
        self.print_title('loading service modules')

        if 'services' in self.config:
            for name, service in self.config['services'].items():
                service['name'] = name

        active_services = []
        if 'service' in self.config['args'] and self.config['args']['service']:
            active_services.extend(self.config['args']['service'].split(','))
        elif 'services' in self.config:
            active_services.extend(self.config['services'].keys())

        self.logger.log('Active Services:\n%s\n' % '\n'.join(active_services))

        self.ignore_unchanged_services(active_services)

        for service_name in active_services:
            service = self.config['services'][service_name]
            self.load_service_module(service)

        return active_services

    def load_service_module(self, service):
        service['module'] = None

        if 'config' not in service:
            service['config'] = {}

        if 'service_type' not in service:
            service['service_type'] = 'service'

        adapter_path = service['service_type']

        if 'provider' in service:
            adapter_path = '%s/%s' % (service['provider'], adapter_path)

            self.try_initialize_provider(service['provider'], service)

        if 'providers' in service:
            for provider in service['providers']:
                self.try_initialize_provider(provider, service)

        adapter_name = adapter_path.replace('/', '.')
        service_modules = [
            {
                'name': 'service_adapters.%s' % adapter_name,
                'package': 'service_adapters',
                'file_path': '%s/service_adapters/%s.py' % (self.config['config_path'], adapter_path),
            },
            {
                'file_path': '%s/service_adapters/%s.sh' % (self.config['config_path'], adapter_path),
            },
            {
                'name': 'servicer.builtin.service_adapters.%s' % adapter_name,
                'package': 'servicer.builtin.service_adapters',
                'file_path': '%s/builtin/service_adapters/%s.py' % (self.config['module_path'], adapter_path),
            },
            {
                'file_path': '%s/builtin/service_adapters/%s.sh' % (self.config['module_path'], adapter_path),
            },
        ]
        module = self.load_module_from_paths(service_modules)
        if isinstance(module, str):
            service['shell_script'] = module
        else:
            service['module'] = module

    def ignore_unchanged_services(self, services):
        if 'no_ignore_unchanged' in self.config['args'] and self.config['args']['no_ignore_unchanged']:
            return

        if not 'git' in self.config or not self.config['git']['enabled'] or not self.config['git']['ignore-unchanged']:
            return

        if 'diff-ref' not in self.config['git']:
            self.logger.log('No GIT_DIFF_REF found, aborting change detection.')
            return

        diff_files = self.git.diff(self.config['git']['diff-ref'], name_only=True, merge_base=True)
        self.logger.log('\nChanged Files:')
        self.logger.log('\n'.join(diff_files))

        # TODO: think through what top level 'watch_paths' means
        if 'ignore_paths' in self.config['git']:
            regexes = [self.sanitize_regex(matcher) for matcher in self.config['git']['ignore_paths']]
            matched_files, diff_files = self.match_regexes(diff_files, regexes)

        ignored_services = []
        for service_name in services:
            service = self.config['services'][service_name]
            service_changed_files = diff_files

            if 'git' in service:
                if 'watch_paths' in service['git']:
                    watch_regexes = [self.sanitize_regex(matcher) for matcher in service['git']['watch_paths']]

                    self.logger.log('\nService: %s' % service_name, level='debug')
                    self.logger.log('Matchers:', level='debug')

                    service_changed_files, _ = self.match_regexes(diff_files, watch_regexes)

                if 'ignore_paths' in service['git']:
                    ignore_regexes = [self.sanitize_regex(matcher) for matcher in service['git']['ignore_paths']]
                    _, service_changed_files = self.match_regexes(service_changed_files, ignore_regexes)

                if len(service_changed_files) > 0:
                    self.logger.log('\nChanged Files:', level='debug')
                    self.logger.log('\n'.join(service_changed_files), level='debug')
                else:
                    ignored_services.append(service_name)

        self.logger.log('\nIgnored Services:')
        for sn in ignored_services:
            self.logger.log(sn)
            services.remove(sn)

        self.logger.log('\nChanged Services:')
        self.logger.log('\n'.join(services))

    def sanitize_regex(self, matcher):
        if matcher.startswith('/') and matcher.endswith('/'):
            return matcher[1:-1]

        return matcher.replace('*', '.*')

    # takes a list of strings, and returns a tuple of strings that match and do not match
    def match_regexes(self, strings, regexes):
        if not isinstance(regexes, list):
            regexes = [regexes]

        matches = []
        unmatches = []
        for s in strings:
            for regex in regexes:
                result = re.match(regex, s)

                self.logger.log('%s ~= %s -> %s' % (regex, s, result), level='debug')

                if result:
                    matches.append(s)
                else:
                    unmatches.append(s)

        return matches, unmatches

    def try_initialize_provider(self, provider_name, service):
        if 'no_auth' in self.config['args'] and self.config['args']['no_auth']:
            self.logger.log('skipping provider initialization for %s (no_auth enabled, assuming already authenticated)' % provider_name)
            return

        if 'providers' not in self.config:
            return

        provider = self.config['providers'].get(provider_name)

        if provider == None:
            self.logger.log('ERROR: no provider definition found for: %s' % provider_name, level='error')
            return  # TODO: replace this return with sys.exit(1)

        provider['name'] = provider_name

        should_initialize = not provider.get('initialized')
        force_authenticate = False

        provider_config = copy.deepcopy(provider)

        if service and 'auth' in service:
            self.config_loader.merge_config(provider_config, service['auth'])
            should_initialize = True
            force_authenticate = True

        if should_initialize:
            self.initialize_provider(provider_config, force_authenticate=force_authenticate)
            provider['initialized'] = True

        if service:
            service['config']['initialized_provider'] = provider_config

    def initialize_provider(self, provider, force_authenticate=False):
        self.print_title('intializing provider: %s' % provider['name'])
        self.logger.log('force_authenticate: %s' % force_authenticate, level='debug')

        if 'libraries' in provider and provider['libraries']:
            self.run('%s install %s' % (os.getenv('PIP_EXE', 'pip'), ' '.join(provider['libraries'])))
        if 'auth_script' in provider and provider['auth_script']:
            self.logger.log('authenticating with: %s' % provider['name'])
            auth_script_paths = [
                { 'file_path': '%s/auth/%s.sh' % (self.config['config_path'], provider['name']) },
                { 'file_path': '%s/builtin/auth/%s.sh' % (self.config['module_path'], provider['name']) },
            ]
            auth_script_path = self.load_module_from_paths(auth_script_paths)
            provider['auth_script_path'] = auth_script_path
            self.run(auth_script_path)
        if 'config' in provider:
            auth_modules = [
                {
                    'name': 'auth_adapters.%s' % provider['name'],
                    'package': 'auth_adapters',
                    'file_path': '%s/auth_adapters/%s.py' % (self.config['config_path'], provider['name']),
                },
                {
                    'name': 'servicer.builtin.auth_adapters.%s' % provider['name'],
                    'package': 'servicer.builtin.auth_adapters',
                    'file_path': '%s/builtin/auth_adapters/%s.py' % (self.config['module_path'], provider['name']),
                },
            ]
            module = self.load_module_from_paths(auth_modules)
            auth = module.AuthAdapter(provider['config'], logger=self.logger)

            if force_authenticate or not auth.current_user():
                auth.authenticate()

            self.logger.log('Current User: %s' % auth.current_user())

    def load_module_from_paths(self, modules):
        for mp in modules:
            self.logger.log('searching for module at: %s' % mp['file_path'], level='debug')

            if os.path.exists(mp['file_path']):
                if 'name' in mp:
                    self.logger.log('importing: %s:%s' % (mp['name'], mp['package']), level='debug')

                    module = importlib.import_module(mp['name'])
                    return module
                else:
                    self.logger.log('found matching executable: %s' % mp['file_path'])
                    return mp['file_path']

        self.logger.log('no modules found!')
        sys.exit(1)

    def load_steps(self):
        self.steps = {}
        self.step_order = []

        if 'steps' in self.config:
            for step in self.config['steps']:
                if step['name'] == 'destroy' and not ('destroy' in self.config['args'] and self.config['args']['destroy']):
                    continue

                self.steps[step['name']] = step
                self.step_order.append(step['name'])

        if 'step' in self.config['args'] and self.config['args']['step']:
            self.active_steps = self.config['args']['step'].split(',')
        else:
            self.active_steps = self.step_order.copy()

        print(self.active_steps)

    def run_service_steps(self):
        self.print_title('executing service-steps')
        self.logger.log(json.dumps(self.service_step_order, indent=4))
        self.logger.log()

        service_steps = [item for sublist in self.service_step_order for item in sublist]

        if 'destroy' in self.config['args'] and self.config['args']['destroy']:
            self.print_title('destroying services (in reverse dependency order)')
            destroyed_services = set()
            destroy_service_steps = []

            for ss in reversed(service_steps):
                service_name = ss.split(':')[0]
                if service_name not in destroyed_services:
                    destroyed_services.add(service_name)

                    if 'steps' in self.config['services'][service_name] and 'destroy' in self.config['services'][service_name]['steps']:
                        destroy_step = '%s:%s' % (service_name, 'destroy')
                        destroy_service_steps.append(destroy_step)

            service_steps = destroy_service_steps
            self.logger.log(json.dumps(service_steps, indent=4))

        for service_step_name in service_steps:
            ss_pieces = service_step_name.split(':')
            service_name = ss_pieces[0]
            step_name = ss_pieces[1]

            self.print_title('service-step: %s:%s' % (service_name, step_name))

            step = self.steps[step_name]
            service = self.config['services'][service_name]
            service_step = service['steps'][step_name]

            self.logger.log('step:', level='debug')
            self.logger.log(json.dumps(step, indent=4, sort_keys=True, default=str), level='debug')
            self.logger.log(level='debug')
            self.logger.log('service:', level='debug')
            self.logger.log(json.dumps(service, indent=4, sort_keys=True, default=str), level='debug')
            self.logger.log(level='debug')

            if 'config' in step and 'requires_service_environment' in step['config']:
                if step['config']['requires_service_environment'] and self.service_environment == None:
                    self.logger.log('skipping, no valid service environment found for step: %s' % step_name)
                    continue

            self.run_service_step(service, service_step)

            # TODO: rethink and standardize this termination process
            if 'TERMINATE_BUILD' in os.environ:
                self.logger.log('build termination requested, stopping with code: %s' % os.environ['TERMINATE_BUILD'])
                sys.exit(int(os.environ['TERMINATE_BUILD']))

        self.tag_build()
        self.logger.log('\nBuild Complete.')

    def run_service_step(self, service, service_step):
        if 'module' not in service:
            self.load_service_module(service)

        self.run_commands(service_step.get('commands'))

        if 'config' in service_step:
            config = service_step.get('config')

            if 'git' in self.config and self.config['git']['enabled']:
                if 'git' not in config:
                    config['git'] = {}
                config['git']['module'] = self.git

            interpolation_params = {**self.config, **os.environ}
            self.token_interpolator.interpolate_tokens(config, interpolation_params)

            adapter = service['module'].Service(config, logger=self.logger)
            adapter.full_config = self.config

            if 'dry' in self.config['args'] and self.config['args']['dry']:
                self.logger.log('DRY: adapter.up(): %s' % service.get('service_type'))
            else:
                results = adapter.up()

                if results:
                    service_step['results'] = results
                    self.logger.log('results: ')
                    self.logger.log(json.dumps(results, indent=4, sort_keys=True, default=str))

        self.run_commands(service_step.get('post_commands'))

    def run_commands(self, commands):
        if not commands:
            return

        for c in commands:
            if isinstance(c, dict):
                if 'env_var' in c:
                    result = self.run_command(c['command'])
                    os.environ[c['env_var']] = result['stdout'].strip()
            else:
                self.run_command(c)

    def run_command(self, command):
        interpolation_params = {**self.config, **os.environ}
        command = self.token_interpolator.replace_tokens(command, interpolation_params)

        if 'dry' in self.config['args'] and self.config['args']['dry']:
            self.logger.log('DRY: executing: %s' % command)
            return

        return self.run(command)

    def print_title(self, message='', border='----'):
        inner_text = ' %s ' % message
        border_text = border

        while len(border_text) < len(inner_text):
            border_text = '%s %s' % (border_text, border)

        self.logger.log()
        self.logger.log(border_text)
        self.logger.log(inner_text)
        self.logger.log(border_text)
        self.logger.log()

def main():
    Servicer().run_service_steps()

if __name__ == '__main__':
    main()
