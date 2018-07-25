from .aws_service import AWSService
import os
import requests
from botocore.client import ClientError

class Service(AWSService):
    def up(self):
        super().up()

        self.s3 = self.boto3.resource('s3')

        self.ensure_bucket()

        if 'steps' in self.config:
            self.run_steps(self.config['steps'])

    def down(self):
        super().down()

    def ensure_bucket(self):
        bucket_args = {
            'Bucket': self.config['bucket'],
        }

        print('ensuring bucket exists: %s' % bucket_args['Bucket'])
        try:
            self.s3.meta.client.head_bucket(**bucket_args)
        except ClientError:
            bucket_args['CreateBucketConfiguration'] = {
                'LocationConstraint': self.config['region'],
            }
            bucket = self.s3.create_bucket(**bucket_args)

    def run_steps(self, steps):
        for step in steps:
            getattr(self, step['type'])(**step['args'])

    def sync(self, from_path=None, to_path=None, delete=True):
        command = 'aws s3 sync %s %s' % (from_path, to_path)
        if delete:
            command = '%s --delete' % command
        self.run(command, shell=True)

    def url_to_s3(self, key=None, url=None):
        print('downloading: %s -> s3://%s/%s' % (url, self.config['bucket'], key))
        req_for_image = requests.get(url, stream=True)
        file_object_from_req = req_for_image.raw
        req_data = file_object_from_req.read()

        self.s3.Bucket(self.config['bucket']).put_object(Key=key, Body=req_data)
