import os
import sys
import re
import hashlib
import requests
from requests.auth import HTTPBasicAuth
from ..base_service import BaseService

class Service(BaseService):
    def __init__(self, config):
        super().__init__(config)
        self.pypirc_path = os.getenv('PYPIRC_PATH', '%s/.pypirc' % os.environ['HOME'])
        self.pip_conf_path = os.getenv('PIP_CONF_PATH', '%s/.pip/pip.conf' % os.environ['HOME'])

    def up(self):
        super().up()

        if 'steps' in self.config:
            self.run_steps(self.config['steps'])

    def run_steps(self, steps):
        for step in steps:
            getattr(self, step['type'])(**step.get('args', {}))

    def setup_py(self, command):
        self.run('%s setup.py %s' % (os.getenv('PYTHON_EXE', 'python'), command)

    def generate_pypi_config(self, config=None):
        if config:
            self.pypi_config = config
        else:   # setup defaults
            self.pypi_config = {
                'pypirc': {
                    'servers': {
                        'testpypi': {
                            'repository': 'https://test.pypi.org/legacy/',
                            'username': os.environ['PYPI_USERNAME'],
                            'password': os.environ['PYPI_PASSWORD'],
                        },
                        'pypi': {
                            'username': os.environ['PYPI_USERNAME'],
                            'password': os.environ['PYPI_PASSWORD'],
                        },
                    },
                },
            }

            if os.getenv('PYPI_REPOSITORY'):
                pieces = os.environ['PYPI_REPOSITORY'].split('://')
                protocol = pieces[0]
                domain = pieces[1]

                url = '%s://%s:%s@%s' % (protocol, os.environ['PYPI_USERNAME'], os.environ['PYPI_PASSWORD'], domain)
                self.pypi_config['pip.conf'] = {
                    'entries': [{
                        'scope': 'global',
                        'args': {
                            'extra-index-url': url,
                        },
                    }],
                }
        if 'pypirc' in self.pypi_config:
            self.generate_pypirc()
        if 'pip.conf' in self.pypi_config:
            self.generate_pip_conf()

    def generate_pypirc(self):
        pypirc_config = self.pypi_config['pypirc']

        if 'path' in pypirc_config:
            self.pypirc_path = pypirc_config.pop('path')

        print('generating .pypirc at %s' % self.pypirc_path)
        os.makedirs(os.path.dirname(self.pypirc_path), exist_ok=True)
        with open(self.pypirc_path, 'w') as pypirc:
            pypirc.write('[distutils]\n')
            pypirc.write('index-servers =\n')
            for server, config in pypirc_config['servers'].items():
                pypirc.write('    %s\n' % server)
            pypirc.write('\n')

            for server, config in pypirc_config['servers'].items():
                pypirc.write('[%s]\n' % server)
                for field in 'repository username password'.split():
                    if field in config:
                        pypirc.write('%s: %s\n' % (field, config[field]))
                pypirc.write('\n')

        print('.pypirc written to %s' % self.pypirc_path)

    def generate_pip_conf(self):
        pip_conf_config = self.pypi_config['pip.conf']

        if 'path' in pip_conf_config:
            self.pip_conf_path = pip_conf_config.pop('path')

        print('generating pip.conf at %s' % self.pip_conf_path)
        os.makedirs(os.path.dirname(self.pip_conf_path), exist_ok=True)
        with open(self.pip_conf_path, 'w') as pipconf:
            for config in pip_conf_config['entries']:
                pipconf.write('[%s]\n' % config['scope'])
                for key, value in config['args'].items():
                    pipconf.write('%s = %s\n' % (key, value))
                pipconf.write('\n')

        print('pip.conf written to %s' % self.pip_conf_path)

    def upload(self, server='pypi', path='dist/*'):
        self.run('twine upload --config-file=%s %s -r %s' % (self.pypirc_path, path, server))

    def if_package_versions_exist(self, package_directory=None, action=None):
        regex = re.compile('(.+)-(\d+\.\d+\.\d+)\..+')
        packages = {}

        for f in os.listdir(package_directory):
            if os.path.isfile(os.path.join(package_directory, f)):
                match = regex.search(f)
                package_name = match.group(1)
                version = match.group(2)

                if not package_name in packages:
                    packages[package_name] = []
                packages[package_name].append(version)

        print('found these packages at (%s): %s' % (package_directory, packages))

        existing_packages = []
        for package, versions in packages.items():
            existing_versions = self.get_versions(package_name=package)
            intersection = set.intersection(set(existing_versions), set(versions))
            if bool(intersection):
                existing_packages.extend(['%s-%s' % (package, i) for i in intersection])

        if existing_packages and action:
            if action == 'error':
                print(existing_packages)
                raise ValueError('Package already exists! %s-%s' % (package_name, version))

    def if_package_version_exists(self, package_name=None, version=None, action=None):
        print('checking for %s-%s...' % (package_name, version))

        exists = version in self.get_versions(package_name)
        if exists and action:
            if action == 'error':
                raise ValueError('Package already exists! %s-%s' % (package_name, version))

        return exists

    def get_versions(self, package_name=None):
        result = self.pip('install %s==' % package_name)
        regex = re.compile('\(from versions: (.*)\)')
        match = regex.search(result['stdout'])

        versions = []
        if match:
            versions.extend(match.group(1).split(', '))

        print('package: %s' % package_name)
        print('versions: %s' % versions)

        return versions

    def pip(self, command, hide_output=True):
        result = self.run('PIP_CONFIG_FILE=%s %s %s' % (self.pip_conf_path, os.getenv('PIP_EXE', 'pip'), command), check=False, hide_output=hide_output)
        return result
