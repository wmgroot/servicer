import os
import sys
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

    def load_repository_config(self, config=None):
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

    def generate_pypirc(self, path='%s/.pypirc' % os.environ['HOME']):
        print('generating .pypirc at %s' % path)
        with open(path, 'w') as pypirc:
            pypirc.write('[distutils]\n')
            pypirc.write('index-servers =\n')
            for server, config in self.repository_config['servers'].items():
                pypirc.write('    %s\n' % server)
            pypirc.write('\n')

            for server, config in self.repository_config['servers'].items():
                pypirc.write('[%s]\n' % server)
                for field in 'repository username password'.split():
                    if field in config:
                        pypirc.write('%s: %s\n' % (field, config[field]))
                pypirc.write('\n')

        print('.pypirc written to %s' % path)

    def upload(self, server='pypi', path='dist/*'):
        self.run('twine upload %s -r %s' % (path, server))
