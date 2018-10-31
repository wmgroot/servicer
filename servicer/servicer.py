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
from .generate_ci_config import generate_ci_config
from .git import Git
from .run import run
from .token_interpolator import TokenInterpolator

class Servicer():
    def __init__(self, args=None, init=True):
        if not init:
            return

        self.datetime = datetime

        self.version = pkg_resources.get_distribution('servicer').version
        self.run = run
        self.token_interpolator = TokenInterpolator()

        if args == None:
            args = vars(self.load_arguments())

        if 'version' in args and args['version']:
            print(self.version)
            sys.exit(0)

        print('servicer version: %s' % self.version)

        self.load_environment(args)

        self.config_loader = ConfigLoader(args)
        self.config = self.config_loader.load_config()

        self.normalize_ci_environment()
        self.determine_service_environment()

        self.config_loader.interpolate_config(self.config)

        if os.getenv('DEBUG'):
            print('Services Config:')
            print(json.dumps(self.config, indent=4, sort_keys=True, default=str))

        if 'show_config' in self.config['args'] and self.config['args']['show_config']:
            print('Services Config:')
            print(json.dumps(self.config, indent=4, sort_keys=True, default=str))
            sys.exit(0)

        self.git_init()

        self.load_steps()
        self.active_services = self.load_service_modules()
        # self.service_step_order = self.order_service_steps(self.active_services)
        self.dependency_grapher = DependencyGrapher(self.config, self.active_services, self.steps, self.step_order, self.active_steps)
        self.service_step_order = self.dependency_grapher.order_service_steps(self.active_services)

        if 'generate_ci' in self.config['args'] and self.config['args']['generate_ci']:
            generate_ci_config(config=config, path='.')
            sys.exit(0)

    def load_arguments(self):
        parser = argparse.ArgumentParser(description='Process deployment options.')
        parser.add_argument('--generate_ci', action='store_true', help='generate a ci config file, do not run any deploy options')
        parser.add_argument('--service', help='deploy only the provided service')
        parser.add_argument('--services_file', default='services.yaml', help='custom path to your services config file (default is services.yaml)')
        parser.add_argument('--servicer_config_path', default='%s/.servicer' % os.getcwd(), help='path to your servicer directory (default is ./servicer)')
        parser.add_argument('--env_file_paths', default='%s/.servicer/.env.yaml:%s/.servicer/.env.yaml' % (os.getenv('HOME'), os.getcwd()), help='paths to your local .env files, colon-separated')
        parser.add_argument('--step', help='perform the comma-separated build steps, defaults to all steps')
        parser.add_argument('--show_config', action='store_true', help='prints the interpolated config file')
        parser.add_argument('--no_ignore_unchanged', action='store_true', help='disables ignoring services through change detection')
        parser.add_argument('--no_tag', action='store_true', help='disables build tagging')
        parser.add_argument('--no_auth', action='store_true', help='disables build authentication, useful if you are already authenticated locally')
        parser.add_argument('--ignore_dependencies', action='store_true', help='disables automatic dependency execution')
        parser.add_argument('--version', action='store_true', help='display the package version')
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
        print('checking for (.env.yaml) at (%s)' % path)
        if os.path.exists(path):
            print('(.env.yaml) found, including these arguments:')

            yaml_dict = yaml.load(open(path))
            for key, value in yaml_dict.items():
                os.environ[key] = value
                print(key)
            print()

    def normalize_ci_environment(self):
        if 'ci' not in self.config:
            return

        self.print_title('normalizing CI environment')

        self.config['ci']['adapters'] = {}
        for p in self.config['ci']['providers']:
            print('CI Adapter: %s' % p)
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
            self.config['ci']['adapters'][p] = module.CIAdapter()

        for ci_adapter in self.config['ci']['adapters'].values():
            ci_adapter.convert_environment_variables()

    def determine_service_environment(self):
        print()
        self.service_environment = os.getenv('SERVICE_ENVIRONMENT') or self.get_service_environment(os.getenv('BRANCH', 'local'))

        print('branch: %s' % os.getenv('BRANCH'))
        print('service environment: %s' % self.service_environment)
        if self.service_environment:
            os.environ['SERVICE_ENVIRONMENT'] = self.service_environment

    def get_service_environment(self, branch):
        service_environment = None
        if 'environment' not in self.config or 'mappings' not in self.config['environment']:
            return service_environment

        mappings = self.config['environment']['mappings']
        service_environment, self.service_environment_config = self.map_service_environment(branch, mappings)

        if service_environment:
            for ch in ['\\', '/', '_']:
                if ch in service_environment:
                    service_environment = service_environment.replace(ch, '-')

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

        git_args = { 'hide_output': 'DEBUG' not in os.environ }
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

        if 'fetch-tags' in self.config['git'] and self.config['git']['fetch-tags']:
            self.run('git fetch --tags')

        if 'GIT_DIFF_REF' in os.environ:
            result = self.run('git cat-file -t %s' % os.environ['GIT_DIFF_REF'], check=False)
            if result['status'] != 0:
                print('Invalid GIT_DIFF_REF provided!')
            else:
                self.config['git']['diff-ref'] = os.environ['GIT_DIFF_REF']

        if 'BRANCH' in os.environ:
            if self.config['git']['diff-tagging-enabled'] and 'diff-ref' not in self.config['git']:
                servicer_tag_part = 'servicer-%s' % self.git.sanitize_tag(os.environ['BRANCH'])
                self.build_tags = [t for t in self.git.list_tags() if t.startswith(servicer_tag_part)]

                if os.getenv('DEBUG'):
                    print('branch tag: %s' % servicer_tag_part)
                    print('matching tags:')
                    print('\n'.join(self.build_tags))

                if len(self.build_tags) > 0:
                    self.config['git']['diff-ref'] = self.build_tags[-1]

            if 'diff-defaults-to-latest-tag' in self.config['git'] and self.config['git']['diff-defaults-to-latest-tag'] and 'diff-ref' not in self.config['git']:
                result = self.run('git describe --tags --abbrev=0 --match "servicer-*" HEAD', check=False)

                if result['status'] == 0:
                    latest_tag = result['stdout'].strip()
                    if latest_tag:
                        print('defaulting to latest servicer git tag')
                        self.config['git']['diff-ref'] = latest_tag

            # TODO: remove this feature in next breaking update
            if 'default-branch' in self.config['git'] and self.config['git']['default-branch'] and 'diff-ref' not in self.config['git']:
                if os.environ['BRANCH'] != self.config['git']['default-branch']:
                    print('defaulting Git Diff Ref to default-branch')
                    self.config['git']['diff-ref'] = 'origin/%s' % self.config['git']['default-branch']

        if 'diff-ref' in self.config['git']:
            print('Git Diff Ref: %s\n' % self.config['git']['diff-ref'])

        if self.config['git']['ignore-servicer-commits'] and 'diff-ref' in self.config['git']:
            authors = self.git.authors_for_changes_ahead_of_ref(self.config['git']['diff-ref'])
            print('Commit authors: %s' % authors)
            if 'servicer' in authors:
                print('Automated servicer changes were detected, skipping this build.')
                sys.exit(0)

    def tag_build(self):
        if not 'git' in self.config or not self.config['git']['enabled']:
            return

        if not self.config['git']['diff-tagging-enabled'] or 'BUILD_NUMBER' not in os.environ:
            return

        if 'no_tag' in self.config['args'] and self.config['args']['no_tag']:
            return

        servicer_tag = self.servicer_git_tag()
        if servicer_tag:
            print('Build complete, tagging: %s' % servicer_tag)
            self.git.tag(servicer_tag, push=True)

            print('Removing old tags...')
            if servicer_tag in self.build_tags:
                self.build_tags.remove(servicer_tag)
            self.remove_stale_tags(self.build_tags)

    def remove_stale_tags(self, tags):
        self.git.delete_tag(tags)

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

        print('Active Services:\n%s\n' % '\n'.join(active_services))

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
            print('No GIT_DIFF_REF found, aborting change detection.')
            return

        diff_files = self.git.diff(self.config['git']['diff-ref'], name_only=True, merge_base=True)
        print('\nChanged Files:')
        print('\n'.join(diff_files))

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

                    if os.getenv('DEBUG'):
                        print('\nService: %s' % service_name)
                        print('Matchers:')

                    service_changed_files, _ = self.match_regexes(diff_files, watch_regexes)

                if 'ignore_paths' in service['git']:
                    ignore_regexes = [self.sanitize_regex(matcher) for matcher in service['git']['ignore_paths']]
                    _, service_changed_files = self.match_regexes(service_changed_files, ignore_regexes)

                if len(service_changed_files) > 0:
                    if os.getenv('DEBUG'):
                        print('\nChanged Files:')
                        print('\n'.join(service_changed_files))
                else:
                    ignored_services.append(service_name)

        print('\nIgnored Services:')
        for sn in ignored_services:
            print(sn)
            services.remove(sn)

        print('\nChanged Services:')
        print('\n'.join(services))

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

                if os.getenv('DEBUG'):
                    print('%s ~= %s -> %s' % (regex, s, result))

                if result:
                    matches.append(s)
                else:
                    unmatches.append(s)

        return matches, unmatches

    def try_initialize_provider(self, provider_name, service):
        if 'no_auth' in self.config['args'] and self.config['args']['no_auth']:
            print('skipping provider initialization for %s (no_auth enabled, assuming already authenticated)' % provider_name)
            return

        provider = self.config['providers'].get(provider_name)

        if provider == None:
            return

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
        print('force_authenticate: %s' % force_authenticate)

        if 'libraries' in provider and provider['libraries']:
            self.run('%s install %s' % (os.getenv('PIP_EXE', 'pip'), ' '.join(provider['libraries'])))
        if 'auth_script' in provider and provider['auth_script']:
            print('authenticating with: %s' % provider['name'])
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
            auth = module.AuthAdapter(provider['config'])

            if force_authenticate or not auth.current_user():
                auth.authenticate()

            print('Current User: %s' % auth.current_user())

    def load_module_from_paths(self, modules):
        for mp in modules:
            if os.getenv('DEBUG'):
                print('searching for module at: %s' % mp['file_path'])
            if os.path.exists(mp['file_path']):
                if 'name' in mp:
                    if os.getenv('DEBUG'):
                        print('importing: %s:%s' % (mp['name'], mp['package']))

                    module = importlib.import_module(mp['name'])
                    return module
                else:
                    print('found matching executable: %s' % mp['file_path'])
                    return mp['file_path']

        print('no module found!')
        sys.exit(1)

    def load_steps(self):
        self.steps = {}
        self.step_order = []
        if 'steps' in self.config:
            for step in self.config['steps']:
                self.steps[step['name']] = step
                self.step_order.append(step['name'])

        if 'step' in self.config['args'] and self.config['args']['step']:
            self.active_steps = self.config['args']['step'].split(',')
        else:
            self.active_steps = self.step_order.copy()

    def run_service_steps(self):
        self.print_title('running service steps')
        print(json.dumps(self.service_step_order, indent=4))
        print()

        service_steps = [item for sublist in self.service_step_order for item in sublist]

        for service_step_name in service_steps:
            ss_pieces = service_step_name.split(':')
            service_name = ss_pieces[0]
            step_name = ss_pieces[1]

            self.print_title('service-step: %s:%s' % (service_name, step_name))

            step = self.steps[step_name]
            service = self.config['services'][service_name]
            service_step = service['steps'][step_name]

            if os.getenv('DEBUG'):
                print('step:')
                print(json.dumps(step, indent=4, sort_keys=True, default=str))
                print()
                print('service:')
                print(json.dumps(service, indent=4, sort_keys=True, default=str))
                print()

            if 'config' in step and 'requires_service_environment' in step['config']:
                if step['config']['requires_service_environment'] and self.service_environment == None:
                    print('skipping, no valid service environment found for step: %s' % step_name)
                    continue

            self.run_service_step(service, service_step)

            # TODO: rethink and standardize this termination process
            if 'TERMINATE_BUILD' in os.environ:
                print('build termination requested, stopping with code: %s' % os.environ['TERMINATE_BUILD'])
                sys.exit(int(os.environ['TERMINATE_BUILD']))

        self.tag_build()
        print('\nBuild Complete.')

    def run_service_step(self, service, service_step):
        if 'module' not in service:
            self.load_service_module(service)

        # allow interpolation of result values from prior service-steps
        self.token_interpolator.interpolate_tokens(service_step, self.config)

        commands = service_step.get('commands')
        if commands:
            for c in commands:
                self.run(c)

        if 'config' in service_step:
            config = service_step.get('config')

            if 'git' in self.config and self.config['git']['enabled']:
                if 'git' not in config:
                    config['git'] = {}
                config['git']['module'] = self.git

            adapter = service['module'].Service(config)
            adapter.full_config = self.config
            results = adapter.up()

            if results:
                service_step['results'] = results
                print('results: ')
                print(json.dumps(results, indent=4, sort_keys=True, default=str))

        post_commands = service_step.get('post_commands')
        if post_commands:
            for c in post_commands:
                self.run(c)

    def print_title(self, message='', border='----'):
        inner_text = ' %s ' % message
        border_text = border

        while len(border_text) < len(inner_text):
            border_text = '%s %s' % (border_text, border)

        print()
        print(border_text)
        print(inner_text)
        print(border_text)
        print()

def main():
    Servicer().run_service_steps()

if __name__ == '__main__':
    main()
