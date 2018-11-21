from .base_auth_adapter import BaseAuthAdapter

import urllib.request
import os
from servicer.run import run

class AuthAdapter(BaseAuthAdapter):
    def __init__(self, config, logger=None):
        super().__init__(config, logger=logger)
        self.run = run

        self.sonarqube_token = os.getenv('SONARQUBE_TOKEN', self.config.get('auth_token'))

        self.scanner_version = self.config['scanner_version']
        self.scanner_path = self.config.get('scanner_path', './')

        if self.scanner_path.endswith('/'):
            self.scanner_path = '%ssonar-scanner-cli-%s' % (self.scanner_path, self.scanner_version)

    def authenticate(self):
        if self.sonarqube_token:
            self.ensure_install()
        else:
            self.logger.log('no sonarqube token found, skipping')

    def ensure_install(self):
        if os.path.exists(self.scanner_path):
            self.logger.log('found sonar-scanner installation at %s' % self.scanner_path)
        else:
            download_file = 'sonar-scanner-cli-%s.zip' % self.scanner_version
            download_directory = os.path.dirname(self.scanner_path)
            download_path = '%s/%s' % (download_directory, download_file)
            url = 'https://binaries.sonarsource.com/Distribution/sonar-scanner-cli/%s' % download_file

            file_path = '%s.zip' % self.scanner_path
            self.logger.log('downloading sonar-scanner from %s to %s' % (url, download_path))
            urllib.request.urlretrieve(url, download_path)

            self.run('unzip -d `dirname %s` %s' % (download_path, download_path))
            self.run('rm %s' % download_path)

            extracted_directory = 'sonar-scanner-%s' % self.scanner_version
            self.run('mv %s/%s %s' % (download_directory, extracted_directory, self.scanner_path))
