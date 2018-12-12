# from .gcloud_service import GCloudService
from ..task_service import Service as BaseService
import os
import requests
from google.cloud import storage

class Service(BaseService):
    def up(self):
        self.project = self.config.get('project', os.environ['GCLOUD_PROJECT'])
        self.gs = storage.Client(project=self.project)

        self.bucket_name = self.config['bucket']
        self.bucket = storage.Bucket(self.gs, name=self.bucket_name)
        self.ensure_bucket()

        super().up()

    def down(self):
        super().down()

    def ensure_bucket(self):
        self.logger.log('ensuring bucket exists: %s' % self.bucket_name)

        region = self.config.get('region', os.getenv('GCLOUD_REGION'))
        if region:
            self.bucket.location = region

        if not self.bucket.exists():
            self.bucket.create()

    def blob(self, blob_arg, operation, operation_arg=None):
        op_args = []
        if operation_arg:
            arg = open(operation_arg, 'wb') if operation == 'download_to_file' else operation_arg
            op_args.append(arg)

        self.logger.log('executing blob operation: (%s).%s(%s)' % (blob_arg, operation, operation_arg))

        blob = self.bucket.blob(blob_arg)
        getattr(blob, operation)(*op_args)

        if operation_arg and operation == 'download_to_file':
            op_args[0].close()
