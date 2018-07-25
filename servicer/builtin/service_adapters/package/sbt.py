import os
import sys
import re

from .base_package import Service as BasePackageService

class Service(BasePackageService):
    def __init__(self, config=None):
        super().__init__(config=config)
        self.sbt_credentials_path = os.getenv('SBT_CREDENTIALS_PATH', '%s/.sbt/.credentials' % os.environ['HOME'])

        self.name_regex = re.compile('name\s*:=\s*[\'\"]+(.*?)[\'\"]+')
        self.version_regex = re.compile('version in ThisBuild := [\'\"]+(\d+\.\d+\.\d+\.*\d*)[\'\"]+')
        self.scala_version_regex = re.compile('val scala = [\'\"]+(\d+\.\d+\.\d+)[\'\"]+')
        self.package_version_format = 'version in ThisBuild := "%s"'

    def run_steps(self, steps):
        for step in steps:
            getattr(self, step['type'])(**step.get('args', {}))

    def generate_sbt_credentials(self, credentials=None):
        if credentials:
            self.credentials = credentials
        else:   # setup defaults
            self.credentials = {
                'realm': os.environ['SBT_CREDENTIALS_REALM'],
                'host': os.environ['SBT_CREDENTIALS_HOST'],
                'user': os.environ['SBT_CREDENTIALS_USER'],
                'password': os.environ['SBT_CREDENTIALS_PASSWORD'],
            }

        print('generating credentials at %s' % self.sbt_credentials_path)
        os.makedirs(os.path.dirname(self.sbt_credentials_path), exist_ok=True)
        with open(self.sbt_credentials_path, 'w') as creds:
            for key, value in self.credentials.items():
                creds.write('%s=%s\n' % (key, value))

        print('credentials written to %s' % self.sbt_credentials_path)

    def read_package_info(self, package_info={}):
        super().read_package_info(package_info=package_info)

        self.package_info['scala_version'] = self.scala_version(self.config['package_info']['scala_version_file_path'])

    def scala_version(self, path):
        with open(path) as f:
            text = f.read()
            result = self.scala_version_regex.search(text)

            if result:
                return result.groups()[0]
            else:
                raise ValueError('Package version not defined at: %s' % path)

    # only works with Artifactory :(
    def get_existing_versions(self, **package_info):
        import requests
        from requests.auth import HTTPBasicAuth

        minor_scala_version = '.'.join(package_info['scala_version'].split('.')[0:-1])
        package_path = '%s/%s_%s' % (package_info['organization'], package_info['name'], minor_scala_version)
        url = '%s/api/storage/%s/%s' % (os.environ['ARTIFACTORY_ENDPOINT'], package_info['repository'], package_path)

        response = requests.get(
            url,
            auth=HTTPBasicAuth(os.environ['ARTIFACTORY_USERNAME'], os.environ['ARTIFACTORY_PASSWORD']),
        )
        response.raise_for_status()

        body = response.json()
        versions = [child['uri'][1:] for child in body['children'] if child['folder']]

        print('existing versions for: %s' % package_info['name'])
        print(versions)

        return versions
