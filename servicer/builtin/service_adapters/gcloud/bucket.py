from .gcloud_service import GCloudService
import os
import requests
from google.cloud import storage

class Service(GCloudService):
    def up(self):
        super().up()

        self.project = self.config.get('project', os.environ['GCLOUD_PROJECT'])
        self.gs = storage.Client(project=self.project)

        self.bucket = self.config['bucket']
        self.ensure_bucket()

        if 'steps' in self.config:
            self.run_steps(self.config['steps'])

    def down(self):
        super().down()

    def ensure_bucket(self):
        bucket_args = {
            'Bucket': self.config['bucket'],
        }

        print('ensuring bucket exists: %s' % self.bucket)
        bucket = storage.Bucket(self.gs, name=self.bucket)

        region = self.config.get('region', os.getenv('GCLOUD_REGION'))
        if region:
            bucket.location = region

        if not bucket.exists():
            bucket.create()

    def run_steps(self, steps):
        for step in steps:
            getattr(self, step['type'])(**step['args'])
