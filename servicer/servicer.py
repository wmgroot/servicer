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

from .generate_ci_config import generate_ci_config
from .topological_order import toposort2
from .tokens import interpolate_tokens
from .run import run
from .git import Git
from .config_loader import ConfigLoader

class Servicer():
    def __init__(self, args=None):
        self.version = pkg_resources.get_distribution('servicer').version
        self.run = run

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

        self.git_init()

        self.active_services = self.load_service_modules()
        self.service_order = self.order_services(self.active_services)
        self.load_steps()

        if 'generate_ci' in self.config['args'] and self.config['args']['generate_ci']:
            generate_ci_config(config=config, path='.')
            sys.exit(0)

    def load_arguments(self):
        parser = argparse.ArgumentParser(description='Process deployment options.')
        parser.add_argument('--generate_ci', action='store_true', help='generate a ci config file, do not run any deploy options')
        parser.add_argument('--service', help='deploy only the provided service')
        parser.add_argument('--services_file', default='services.yaml', help='custom path to your services config file (default is services.yaml)')
        parser.add_argument('--servicer_config_path', default='%s/.servicer' % os.getcwd(), help='path to your servicer directory (default is ./servicer)')
        parser.add_argument('--env_file_paths', default='~/.servicer/.env.yaml:%s/.env.yaml' % os.getcwd(), help='paths to your local .env files, colon-separated')
        parser.add_argument('--step', help='perform the comma-separated build steps, defaults to all steps')
        parser.add_argument('--no_ignore', action='store_true', help='disables ignoring services through change detection')
        parser.add_argument('--no_tag', action='store_true', help='disables build tagging')
        parser.add_argument('--no_auth', action='store_true', help='disables build authentication, useful if you are already authenticated locally')
        parser.add_argument('--version', action='store_true', help='display the package version')
        return parser.parse_args()

    def load_environment(self, args):
        os.environ['PROJECT_PATH'] = os.environ['PWD']
        os.environ['BUILD_DATETIME'] = str(datetime.utcnow())
        os.environ['BUILD_DATE'] = datetime.now().strftime('%Y-%m-%d')

        if 'env_file_paths' not in args:
            return

        for path in args['env_file_paths'].split(':'):
            self.load_env_file(path)

    def load_env_file(self, path):
        print('checking for (.env.yaml) at (%s)' % path)
        if os.path.exists(path):
            print('(.env.yaml) found, including these arguments:')

            yaml_dict = yaml.load(open(path))
            print(yaml_dict)
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
            print(os.environ['SERVICE_ENVIRONMENT'])

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

            if 'config' not in service:
                service['config'] = {}

            if 'provider' not in service:
                continue

            self.try_initialize_provider(service['provider'], service)

            if 'service_type' not in service:
                continue

            service_modules = [
                {
                    'name': 'service_adapters.%s.%s' % (service['provider'], service['service_type']),
                    'package': 'service_adapters',
                    'file_path': '%s/service_adapters/%s/%s.py' % (self.config['config_path'], service['provider'], service['service_type']),
                },
                {
                    'file_path': '%s/service_adapters/%s/%s.sh' % (self.config['config_path'], service['provider'], service['service_type']),
                },
                {
                    'name': 'servicer.builtin.service_adapters.%s.%s' % (service['provider'], service['service_type']),
                    'package': 'servicer.builtin.service_adapters',
                    'file_path': '%s/builtin/service_adapters/%s/%s.py' % (self.config['module_path'], service['provider'], service['service_type']),
                },
                {
                    'file_path': '%s/builtin/service_adapters/%s/%s.sh' % (self.config['module_path'], service['provider'], service['service_type']),
                },
            ]
            module = self.load_module_from_paths(service_modules)
            if isinstance(module, str):
                service['shell_script'] = service['module']
            else:
                service['module'] = module

        return active_services

    def ignore_unchanged_services(self, services):
        if 'no_ignore' in self.config['args'] and self.config['args']['no_ignore']:
            return

        if not 'git' in self.config or not self.config['git']['enabled'] or not self.config['git']['ignore-unchanged']:
            return

        if 'diff-ref' not in self.config['git']:
            print('No GIT_DIFF_REF found, aborting change detection.')
            return

        # self.git.fetch()
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

    # TODO: handle step-service level dependencies
    def order_services(self, services):
        dependencies = {}
        for service_name in services:
            service = self.config['services'][service_name]
            if 'depends_on' in service:
                # only add dependencies that are in the current list of services
                dependencies[service_name] = set()
                for dep in service['depends_on']:
                    if dep in services:
                        dependencies[service_name].add(dep)
                # dependencies[service_name] = set(service['depends_on'])
            else:
                dependencies[service_name] = set()

        ordered_services = toposort2(dependencies)
        return [item for sublist in ordered_services for item in sublist]

    def load_steps(self):
        self.steps = {}
        self.step_order = []
        if 'steps' in self.config:
            for step in self.config['steps']:
                self.steps[step['name']] = step
                self.step_order.append(step['name'])

        if 'step' in self.config['args'] and self.config['args']['step']:
            self.step_order = self.config['args']['step'].split(',')

    def run_steps(self):
        self.print_title('running service steps')
        print('\n'.join(self.step_order))
        print()
        print('\n'.join(self.service_order))

        for step in self.step_order:
            # TODO: rethink and standardize this process
            if 'TERMINATE_BUILD' in os.environ:
                print('build termination requested, stopping with code: %s' % os.environ['TERMINATE_BUILD'])
                sys.exit(int(os.environ['TERMINATE_BUILD']))

            self.print_title('%s step' % step)

            if step in self.steps and 'config' in self.steps[step]:
                step_config = self.steps[step]['config']

                if os.getenv('DEBUG'):
                    print(step_config)

                if 'requires_service_environment' in step_config and step_config['requires_service_environment'] and self.service_environment == None:
                    print('skipping, no valid service environment found for step: %s' % step)
                    continue

            for service_name in self.service_order:
                service = self.config['services'][service_name]

                if 'steps' in service and step in service['steps']:
                    self.print_title('step-service: %s:%s' % (step, service_name))

                    commands = service['steps'][step].get('commands')
                    if commands:
                        for c in commands:
                            self.run(c)

                    if 'module' in service and 'config' in service['steps'][step]:
                        config = service['steps'][step].get('config')
                        # allow interpolation of prior step-service results
                        interpolate_tokens(config, self.config, ignore_missing_key=True)

                        if 'git' in self.config and self.config['git']['enabled']:
                            if 'git' not in config:
                                config['git'] = {}
                            config['git']['module'] = self.git

                        print('Config:')
                        print(json.dumps(config, indent=4, sort_keys=True, default=str))
                        adapter = service['module'].Service(config)
                        results = adapter.up()

                        if results:
                            service['steps'][step]['results'] = results
                            print('results: ')
                            print(json.dumps(results, indent=4, sort_keys=True, default=str))

                    post_commands = service['steps'][step].get('post_commands')
                    if post_commands:
                        for c in post_commands:
                            self.run(c)

        self.tag_build()
        print('\nBuild Complete.')

    def get_service_environment(self, branch):
        service_environment = None
        if 'environment' not in self.config or 'mappings' not in self.config['environment']:
            return service_environment

        mappings = self.config['environment']['mappings']
        service_environment = self.map_service_environment(branch, mappings)

        if service_environment:
            for ch in ['\\', '/', '_']:
                if ch in service_environment:
                    service_environment = service_environment.replace(ch, '-')

        return service_environment

    def map_service_environment(self, branch, mappings=[]):
        for m in mappings:
            if 'branch' in m:
                if m['branch'].startswith('/') and m['branch'].endswith('/'):
                    regex = m['branch'][1:-1]
                else:
                    regex = '^%s$' % m['branch'].replace('*', '.*')

                print(regex)
                print(branch)
                result = re.match(regex, branch)
                print(result)
                if result:
                    return m.get('environment', branch)
            elif 'tag' in m:
                # TODO: support tag mapping
                pass

        return None

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
    Servicer().run_steps()

if __name__ == '__main__':
    main()
