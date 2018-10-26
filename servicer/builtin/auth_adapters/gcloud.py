from .base_auth_adapter import BaseAuthAdapter

import os
from servicer.run import run

class AuthAdapter(BaseAuthAdapter):
    def __init__(self, config):
        super().__init__(config)
        self.run = run

    def authenticate(self):
        self.run('gcloud -v')

        project = self.config.get('project', os.environ['PROJECT_NAME'])
        compute_zone = self.config.get('compute_zone', os.environ['GCLOUD_ZONE'])
        key_file_path = self.config.get('key_file_path', os.environ['GCLOUD_KEY_FILE_PATH'])

        self.ensure_key_file(key_file_path)
        self.run('gcloud auth activate-service-account --key-file %s' % key_file_path)
        self.run('rm %s' % key_file_path)

        self.run('gcloud auth configure-docker -q')

        self.run('gcloud config set project %s' % project)
        self.run('gcloud config set compute/zone %s' % compute_zone)

    def current_user(self):
        result = self.run('gcloud auth list --filter=status:ACTIVE --format="value(account)"')
        active_users = result['stdout'].strip().split('\n')

        if active_users:
            return active_users[0]

    def ensure_key_file(self, key_file_path):
        if os.path.isfile(key_file_path):
            print('found existing gcloud key-file: %s' % key_file_path)
        else:
            print('generating gcloud key-file: %s' % key_file_path)
            key_file_json = self.config.get('key_file_json', os.environ['GCLOUD_KEY_FILE_JSON'])

            with open(key_file_path, 'w') as out:
                out.write(key_file_json)
