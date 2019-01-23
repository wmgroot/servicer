import os
import glob
import json
import re

from ..service import Service as BaseService
from servicer.git import Git

class Service(BaseService):
    def __init__(self, config=None, logger=None):
        super().__init__(config=config, logger=logger)
        self.package_version_format = None

        if 'git' in config:
            self.git = config['git']['module']

        if 'package_info' not in self.config:
            self.config['package_info'] = {}

        if 'package_file_path' in self.config['package_info'] and 'version_file_path' not in self.config['package_info']:
             self.config['package_info']['version_file_path'] = self.config['package_info']['package_file_path']

    def up(self):
        super().up()

        self.results = {}

        if 'steps' in self.config:
            self.run_steps(self.config['steps'])

        return self.results

    def run_steps(self, steps):
        for step in steps:
            getattr(self, step['type'])(**step.get('args', {}))

    def set_auto_version(self, max_increment=10, auto_detect_version=True):
        self.logger.log('auto-versioning (auto_detect_version=%s)...' % auto_detect_version)

        self.read_package_info(self.config['package_info'])
        if not isinstance(self.package_info, list):
            self.package_info = [self.package_info]

        if auto_detect_version:
            current_increment = 0
            version_changed = False
            while True:
                any_invalid_version = False
                for pi in self.package_info:

                    pi['version_exists'] = self.if_package_version_exists(**pi)
                    if pi['version_exists']:
                        any_invalid_version = True

                if not any_invalid_version:
                    break

                if current_increment > max_increment:
                    raise ValueError('Max package_version auto-increment reached! %s-%s' % (self.package_info[0]['package_name'], self.package_info[0]['version']))

                for pi in self.package_info:
                    if 'version_exists' in pi and pi['version_exists']:
                        pi['version'] = self.increment_version(pi['version'])

                version_changed = True
                current_increment += 1
        else:
            for pi in self.package_info:
                pi['version'] = self.increment_version(pi['version'])
            version_changed = True

        self.logger.log('Automatic version decided: %s' % ['%s:%s' % (pi['name'], pi['version']) for pi in self.package_info])

        if version_changed:
            if 'changed_files' not in self.results:
                self.results['changed_files'] = set()

            for pi in self.package_info:
                self.write_package_version(
                    path=pi['version_file_path'],
                    version=pi['version'],
                )

                self.results['changed_files'].add(pi['version_file_path'])

            self.results['changed_files'] = list(self.results['changed_files'])

    def commit_and_push_changes(self, git_no_verify=False, terminate_on_change=False):
        if 'BRANCH' not in os.environ:
            self.logger.log('No BRANCH defined, skipping commit and push.')
            return

        if self.git.protocol == 'https' and 'GIT_USERNAME' not in os.environ:
            self.logger.log('No GIT_USERNAME defined, skipping commit and push.')
            return

        commit_args = {
            'message': '[servicer] Automated version change.',
        }

        if 'version_file_path' in self.config['package_info']:
            commit_args['add'] = self.config['package_info']['version_file_path']

        commit_result = self.git.commit(**commit_args)
        push_result = self.git.push(ref=os.environ['BRANCH'], no_verify=git_no_verify)

        if commit_result['status'] == 0:
            if terminate_on_change:
                # requests termination of the build after the current step completes
                os.environ['TERMINATE_BUILD'] = '0'
        else:
            self.logger.log('no changes to commit')

    def increment_version(self, version):
        new_version = [int(v) for v in version.split('.')]
        new_version[-1] += 1
        return '.'.join([str(v) for v in new_version])

    def if_package_version_exists(self, **package_info):
        self.logger.log('checking for %s-%s...' % (package_info['name'], package_info['version']))

        version_list = self.get_existing_versions(**package_info)

        self.logger.log('existing versions: %s' % version_list)

        package_info['version_exists'] = package_info['version'] in version_list
        if package_info['version_exists'] and 'action' in package_info:
            if args['action'] == 'error':
                raise ValueError('Package already exists! %s-%s' % (package_info['name'], package_info['version']))

        return package_info['version_exists']

    def get_existing_versions(self, **package_info):
        if 'existing_versions_source' not in package_info:
            raise NameError('Service must provide existing_versions_source.')
        self.logger.log('existing_versions_source is: %s' % package_info['existing_versions_source'])

        versions_list_method_name = "get_existing_%s_versions" % package_info['existing_versions_source']
        versions_list_method = getattr(self, versions_list_method_name)
        version_list = versions_list_method(**package_info)

        return version_list

    def get_existing_gcr_versions(self, **package_info):
        docker_image = package_info['docker_image_path']

        result = self.run('gcloud container images list-tags %s --format=json' % docker_image, hide_output=True)

        tags = set()
        for r in json.loads(result['stdout']):
            tags.update(r['tags'])

        return list(tags)

    def read_package_info(self, package_info={}):
        self.package_info = package_info

        if 'name' not in self.package_info:
            self.package_info['name'] = self.package_name(self.config['package_info']['package_file_path'])

        if 'package_version_format' in self.package_info:
            self.package_version_format = self.package_info['package_version_format']

        if not self.package_version_format:
            raise ValueError('Service must provide package_version_format.')

        if 'version' not in self.package_info:
            if 'version_regex' in self.package_info:
                self.version_regex = re.compile(self.package_info['version_regex'])
            self.package_info['version'] = self.package_version(self.config['package_info']['version_file_path'])
            self.logger.log('package version is %s' % self.package_info['version'])

        self.results['package_name'] = self.package_info['name']
        if isinstance(self.results['package_name'], list):
            self.results['package_name'] = ','.join(self.results['package_name'])
        self.results['package_version'] = self.package_info['version']

        pieces = self.package_info['version'].split('.')
        self.results['package_version_major'] = pieces[0]
        if len(pieces) > 1:
            self.results['package_version_minor'] = pieces[1]
        if len(pieces) > 2:
            self.results['package_version_patch'] = pieces[2]
        if len(pieces) > 3:
            self.results['package_version_revision'] = pieces[3]

    def package_name(self, path):
        with open(path) as f:
            text = f.read()
            result = self.name_regex.search(text)

            if result:
                name = result.groups()[0]
                return name
            else:
                raise ValueError('Package name not defined at: %s' % path)

    def package_version(self, path):
        with open(path) as f:
            text = f.read()
            result = self.version_regex.search(text)

            if result:
                version = result.groups()[0]
                return version
            else:
                raise ValueError('Package version not defined at: %s' % path)

    def write_package_version(self, path, version):
        text = ''
        with open(path) as f:
            text = f.read()

        new_version = self.package_version_format % version
        text = self.version_regex.sub(new_version, text)

        with open(path, 'w') as out:
            out.write(text)
            self.results['package_version'] = version

    def list_file_paths(self, path, match_glob):
        return glob.glob('%s/%s' % (path, match_glob), recursive=True)
