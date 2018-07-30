import os

from ..base_service import BaseService
from servicer.git import Git

class Service(BaseService):
    def __init__(self, config=None):
        super().__init__(config=config)

        self.git = Git()

        if 'package_info' not in self.config:
            self.config['package_info'] = {}

        if 'package_file_path' in self.config['package_info'] and 'version_file_path' not in self.config['package_info']:
             self.config['package_info']['version_file_path'] = self.config['package_info']['package_file_path']

    def up(self):
        super().up()

        if 'steps' in self.config:
            self.run_steps(self.config['steps'])

    def run_steps(self, steps):
        for step in steps:
            getattr(self, step['type'])(**step.get('args', {}))

    def set_auto_version(self, max_increment=10, terminate_on_change=True):
        print('auto-versioning...')
        self.read_package_info(self.config['package_info'])

        current_increment = 0
        version_changed = False
        while True:
            invalid_version = self.if_package_version_exists(**self.package_info)

            if not invalid_version:
                break

            if current_increment > max_increment:
                raise ValueError('Max package_version auto-increment reached! %s-%s' % (self.package_info['package_name'], self.package_info['version']))

            self.package_info['version'] = self.increment_version(self.package_info['version'])
            version_changed = True
            current_increment += 1

        print('Automatic version decided: %s-%s' % (self.package_info['name'], self.package_info['version']))

        if version_changed:
            self.write_package_version(
                path=self.config['package_info']['version_file_path'],
                version=self.package_info['version'],
            )

            if terminate_on_change:
                # requests termination of the build after the current step completes
                os.environ['TERMINATE_BUILD'] = '0'

    def commit_and_push_changes(self, protocol='ssh'):
        commit_args = {
            'message': '[servicer] Automated version change.',
        }

        if 'version_file_path' in self.config['package_info']:
            commit_args['add'] = self.config['package_info']['version_file_path']

        self.git.commit(**commit_args)
        self.git.push(branch=self.git.current_branch(), protocol=protocol)

    def increment_version(self, version):
        new_version = [int(v) for v in version.split('.')]
        new_version[-1] += 1
        return '.'.join([str(v) for v in new_version])

    def if_package_version_exists(self, **package_info):
        print('checking for %s-%s...' % (package_info['name'], package_info['version']))

        exists = package_info['version'] in self.get_existing_versions(**package_info)
        if exists and 'action' in package_info:
            if args['action'] == 'error':
                raise ValueError('Package already exists! %s-%s' % (package_info['name'], package_info['version']))

        return exists

    def read_package_info(self, package_info={}):
        self.package_info = package_info
        self.package_info['name'] = self.package_name(self.config['package_info']['package_file_path'])
        self.package_info['version'] = self.package_version(self.config['package_info']['version_file_path'])

    def package_name(self, path):
        with open(path) as f:
            text = f.read()
            result = self.name_regex.search(text)

            if result:
                return result.groups()[0]
            else:
                raise ValueError('Package version not defined at: %s' % path)

    def package_version(self, path):
        with open(path) as f:
            text = f.read()
            result = self.version_regex.search(text)

            if result:
                return result.groups()[0]
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
