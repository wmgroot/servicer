from .base_auth_adapter import BaseAuthAdapter

import urllib.request
import os
from servicer.run import run

class AuthAdapter(BaseAuthAdapter):
    def __init__(self, config, logger=None):
        super().__init__(config, logger=logger)
        self.run = run

        self.version = self.config['version']
        self.architecture = self.config.get('architecture', 'amd64')
        self.os = self.run('uname -s')['stdout'].strip().lower()
        self.path = self.config.get('path', '/usr/local/bin/')
        self.name = 'packer_%s_%s_%s' % (self.version, self.os, self.architecture)

        if self.path.endswith('/'):
            self.path += self.name

    def authenticate(self):
        result = self.run('packer --version', check=False)
        if result['status'] == 0 and result['stdout'].strip() == self.version:
            self.logger.log('packer version %s is already installed' % self.version)
        else:
            self.install()

    def install(self):
        self.logger.log('installing packer version: %s' % self.version)

        download_file = '%s.zip' % self.name
        download_directory = os.path.dirname(self.path)
        download_path = '%s/%s' % (download_directory, download_file)
        url = 'https://releases.hashicorp.com/packer/%s/%s' % (self.version, download_file)

        self.run('rm %s/packer' % download_directory)
        file_path = '%s.zip' % self.path
        self.logger.log('downloading packer from %s to %s' % (url, download_path))
        urllib.request.urlretrieve(url, download_path)

        self.run('unzip -d `dirname %s` %s' % (download_path, download_path))
        self.run('rm %s' % download_path)
