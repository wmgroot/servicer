from .base_service import BaseService
from servicer.git import Git

class BasePackageService(BaseService):
    def __init__(self, config=None):
        super().__init__(config=config)

        self.git = Git()

        if 'package_file_path' in self.config and 'version_file_path' not in self.config:
             self.config['version_file_path'] = self.config['package_file_path']

    def set_auto_version(self, max_increment=10):
        print('auto-versioning...')
        self.package_name = self.package_name(self.config['package_file_path'])
        self.package_version = self.package_version(self.config['version_file_path'])

        current_increment = 0
        self.version_changed = False
        while True:
            invalid_version = self.if_package_version_exists(package_name=self.package_name, version=self.package_version)

            if not invalid_version:
                break

            if current_increment > max_increment:
                raise ValueError('Max package_version auto-increment reached! %s-%s' % (self.package_name, self.package_version))

            self.package_version = self.increment_version(self.package_version)
            self.version_changed = True
            current_increment += 1

        print('Automatic version decided: %s-%s' % (self.package_name, self.package_version))

        if self.version_changed:
            self.write_package_version(path=self.config['version_file_path'], version=self.package_version)

    def commit_changes(self):
        if self.version_changed:
            self.git.commit(add=self.config['version_file_path'], message='[servicer] Automated version change.')
            # self.git.push(branch=self.git.current_branch())

    def increment_version(self, version):
        # new_version = version.copy()
        new_version = [int(v) for v in version.split('.')]
        new_version[-1] += 1
        return '.'.join([str(v) for v in new_version])
