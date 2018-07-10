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

    def up(self):
        super().up()

        if 'steps' in self.config:
            self.run_steps(self.config['steps'])

    def down(self):
        super().up()

    def run_steps(self, steps):
        for step in steps:
            getattr(self, step['type'])(**step.get('args', {}))

    def setup_py(self, command):
        self.run('python setup.py %s' % command)

    def generate_pypi_config(self, config=None):
        if config:
            self.repository_config = config
        else:
            self.repository_config = {
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
            }

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

    def generate_pypirc(self, path='%s/.pypirc' % os.environ['HOME']):
        print('generating .pypirc at %s' % path)
        pypirc_config = self.pypi_config['pypirc']

        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as pypirc:
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

        print('.pypirc written to %s' % path)

    def generate_pip_conf(self, path='%s/.pip/pip.conf' % os.environ['HOME']):
        print('generating pip.conf at %s' % path)
        pip_conf_config = self.pypi_config['pip.conf']

        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as pipconf:
            for config in pip_conf_config['entries']:
                pipconf.write('[%s]\n' % config['scope'])
                for key, value in config['args'].items():
                    pipconf.write('%s = %s\n' % (key, value))
                pipconf.write('\n')

        print('pip.conf written to %s' % path)

    def upload(self, server='pypi', path='dist/*'):
        self.run('twine upload %s -r %s' % (path, server))

    def if_package_version_exists(self, package_name=None, version=None, action=None):
        print('checking for %s-%s...' % (package_name, version))

        exists = version in self.get_versions(package_name)
        if exists and action:
            if action == 'error':
                raise ValueError('Package already exists! %s-%s' % (package_name, version))

        return exists

    def get_versions(self, package_name=None):
        result = self.run('pip install %s==' % package_name, check=False, hide_output=True)
        regex = re.compile('\(from versions: (.*)\)')
        match = regex.search(result['stdout'])

        versions = []
        if match:
            versions.extend(match.group(1).split(', '))

        print('package: %s' % package_name)
        print('versions: %s' % versions)

        return versions
