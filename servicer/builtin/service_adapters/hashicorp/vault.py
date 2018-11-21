import sys
import requests
import json

from ..task_service import Service as BaseService
from ..request_service import Service as RequestService

class Service(BaseService, RequestService):
    def __init__(self, config, logger=None):
        super().__init__(config, logger=logger)

        self.base_url = self.config.get('endpoint', os.environ['VAULT_ENDPOINT'])
        self.token = self.config.get('token', os.environ['VAULT_TOKEN'])
        self.base_path = self.config.get('base_path', '')

    def ensure_secret_engine(self, **params):
        response = self.vault_request(url='sys/mounts')
        engines = response.json().keys()
        self.logger.log('engines: %s' % engines)

        if '%s/' % params['path'] not in engines:
            self.logger.log('creating secrets engine: %s(%s)' % (params['path'], params['type']))
            self.logger.log(params)
            response = self.vault_request(
                method='post',
                url='sys/mounts/%s' % params['path'],
                json=params,
            )
            self.logger.log(response.text)
        else:
            self.logger.log('secrets engine already exists: %s(%s)' % (params['path'], params['type']))

    def ensure_policy(self, **params):
        name = params.pop('name')
        self.logger.log('creating policy %s' % name)
        self.logger.log(params)
        response = self.vault_request(
            method='post',
            url='sys/policy/%s' % name,
            json=params,
        )
        self.logger.log(response.text)

    def write(self, **params):
        path = params.pop('path')
        response = self.vault_request(
            method='post',
            url='%s%s' % (self.base_path, path),
            json=params,
        )
        self.logger.log(response.text)

    def read(self, **params):
        response = self.vault_request(url='%s%s' % (self.base_path, params['path']))
        self.logger.log(response.text)

    def vault_request(self, **params):
        if 'headers' not in params:
            params['headers'] = {}
        params['headers']['X-Vault-Token'] = self.token

        return self.request(**params)
