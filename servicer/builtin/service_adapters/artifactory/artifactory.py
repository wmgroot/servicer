import os
import sys
import hashlib
import requests
from requests.auth import HTTPBasicAuth
from ..base_service import BaseService

class Service(BaseService):
    def __init__(self, config):
        super().__init__(config)

        self.endpoint = os.environ['ARTIFACTORY_ENDPOINT']
        self.username = os.environ['ARTIFACTORY_USERNAME']
        self.password = os.environ['ARTIFACTORY_PASSWORD']

    def up(self):
        super().up()

        if 'steps' in self.config:
            self.run_steps(self.config['steps'])

    def down(self):
        super().up()

    def run_steps(self, steps):
        for step in steps:
            getattr(self, step['type'])(**step['args'])

    def upload_files(self, artifactory_directory=None, local_paths=None, errorOnExists=None):
        paths = []
        for lp in local_paths:
            if os.path.isdir(lp):
                for dir_path in os.listdir(lp):
                    paths.append({
                        'ap': '%s/%s' % (artifactory_directory, dir_path),
                        'lp': '%s/%s' % (lp, dir_path),
                    })
            else:
                paths.append({'ap':'%s/%s' % (artifactory_directory, lp), 'lp':lp})

        for path in paths:
            self.upload_file(artifactory_path=path['ap'], local_path=path['lp'], errorOnExists=errorOnExists)

    def upload_file(self, artifactory_path=None, local_path=None, properties=None, errorOnExists=None):
        print('uploading: %s -> %s' % (local_path, artifactory_path))

        if errorOnExists:
            self.file_exists(artifactory_path=artifactory_path, action='error')

        buffer_size = 65536  # read file in 64kb chunks

        md5 = hashlib.md5()
        sha1 = hashlib.sha1()

        with open(local_path, 'rb', buffering=0) as f:
            for block in iter(lambda : f.read(buffer_size), b''):
              md5.update(block)
              sha1.update(block)

        print("MD5: {0}".format(md5.hexdigest()))
        print("SHA1: {0}".format(sha1.hexdigest()))

        url = '%s/%s' % (self.endpoint, artifactory_path)

        if properties:
            for key, value in properties.items():
                url = '%s;%s=%s' % (url, key, value)

        # requests.exceptions.HTTPError: 409 Client Error: Conflict for url ???
        # files = {'file': open(local_path, 'rb')}
        # response = requests.put(
        #     url,
        #     auth=HTTPBasicAuth(self.username, self.password),
        #     headers={'X-Checksum-Sha1':sha1.hexdigest()},
        #     files=files,
        # )
        # response.raise_for_status()

        # workaround for 409 error
        self.run('curl -i -u "%s:%s" -H "X-Checksum-Sha1:%s" -T %s "%s"' % (self.username, self.password, sha1.hexdigest(), local_path, url))

    def download_files(self, artifactory_paths=None, local_directory=None):
        for ap in artifactory_paths:
            file_name = ap.split('/')[-1]
            local_path = '%s/%s' % (local_directory, file_name)
            self.download_file(ap, local_path)

    def download_file(self, artifactory_path=None, local_path=None):
        print('downloading: %s -> %s' % (artifactory_path, local_path))

        url = '%s/%s' % (self.endpoint, artifactory_path)
        response = requests.get(url, auth=HTTPBasicAuth(self.username, self.password), stream=True)
        response.raise_for_status()

        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        with open(local_path, 'wb') as handle:
            for block in response.iter_content(1024):
                handle.write(block)

    def file_exists(self, artifactory_path=None, action=None):
        print('searching for file: %s' % artifactory_path)
        file_name = artifactory_path.split('/')[-1]
        url = '%s/api/search/artifact?name=%s' % (self.endpoint, file_name)

        response = requests.get(url, auth=HTTPBasicAuth(self.username, self.password))
        response.raise_for_status()

        body = response.json()

        exists = False
        for result in body['results']:
            print('result: %s' % result)
            if result['uri'].endswith(artifactory_path):
                exists = True

        if exists and action == 'error':
            raise ValueError('Artifact already exists! %s' % artifactory_path)

        return exists

    def ensure_repository(self, name=None, package_type=None, repo_type='local', description=''):
        key = '%s-%s' % (name, package_type)
        url = '%s/api/repositories/%s' % (self.endpoint, key)

        response = requests.get(url, auth=HTTPBasicAuth(self.username, self.password))
        if response.status_code == 200:
            print('repository already exists: %s' % key)
        elif response.status_code == 400:
            self.create_repository(name=name, package_type=package_type, repo_type=repo_type, description=description)
        else:
            response.raise_for_status()

    def create_repository(self, name=None, package_type=None, repo_type='local', description=''):
        key = '%s-%s' % (name, package_type)
        print('creating repository: %s' % key)

        url = '%s/api/repositories/%s' % (self.endpoint, key)
        data = {
            'key': key,
            'packageType': package_type,
            'rclass': repo_type,
            'description': description,
        }
        print(data)
        response = requests.put(
            url,
            auth=HTTPBasicAuth(self.username, self.password),
            headers={
                # 'Content-Type': 'application/json',
                'Content-Type': 'application/vnd.org.jfrog.artifactory.repositories.LocalRepositoryConfiguration+json',
            },
            json=data,
        )
        response.raise_for_status
        print(response.text)
