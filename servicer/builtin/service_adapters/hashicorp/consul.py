import os
import requests
import json

from ..task_service import Service as BaseService
from ..request_service import Service as RequestService

class Service(BaseService, RequestService):
    def __init__(self, config, logger=None):
        super().__init__(config, logger=logger)

        self.base_url = self.config.get('endpoint', os.environ['CONSUL_ENDPOINT'])
        self.token = self.config.get('token', os.environ['CONSUL_TOKEN'])
        self.base_path = self.config.get('base_path', '')

    def write_file(self, files=[]):
        if not isinstance(files, list):
            files = [files]

        for f in files:
            with open(f['file_path'], 'r') as _file:
                data = _file.read()

                data = self.token_interpolator.replace_tokens(data, os.environ, ignore_missing_key=True)

                consul_url = '%s%s' % (self.base_path, f['consul_path'])
                self.logger.log('writing file to consul: %s -> %s' % (f['file_path'], consul_url))

                self.consul_request(
                    data=data,
                    method='put',
                    url=consul_url,
                )

    def read(self, **params):
        response = self.consul_request(url='%s%s' % (self.base_path, params['path']))
        self.logger.log(response.text)

    def consul_request(self, **params):
        if 'headers' not in params:
            params['headers'] = {}
        params['headers']['X-Consul-Token'] = self.token

        return self.request(**params)
