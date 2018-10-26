import sys
import requests
import json

from ..task_service import Service as BaseService
from ..request_service import Service as RequestService

class Service(BaseService, RequestService):
    def __init__(self, config):
        super().__init__(config)

        self.base_url = self.config.get('endpoint', os.environ['VAULT_ENDPOINT'])
        self.token = self.config.get('token', os.environ['VAULT_TOKEN'])
        self.base_path = self.config.get('base_path', '')

    def ensure_secret_engine(self, **params):
        response = self.vault_request(url='sys/mounts')
        engines = response.json().keys()
        print('engines: %s' % engines)

        if '%s/' % params['path'] not in engines:
            print('creating secrets engine: %s(%s)' % (params['path'], params['type']))
            print(params)
            response = self.vault_request(
                method='post',
                url='sys/mounts/%s' % params['path'],
                json=params,
            )
            print(response.text)
        else:
            print('secrets engine already exists: %s(%s)' % (params['path'], params['type']))

    def ensure_policy(self, **params):
        name = params.pop('name')
        print('creating policy %s' % name)
        print(params)
        response = self.vault_request(
            method='post',
            url='sys/policy/%s' % name,
            json=params,
        )
        print(response.text)

    def write(self, **params):
        path = params.pop('path')
        response = self.vault_request(
            method='post',
            url='%s%s' % (self.base_path, path),
            json=params,
        )
        print(response.text)

    def read(self, **params):
        response = self.vault_request(url='%s%s' % (self.base_path, params['path']))
        print(response.text)

    def vault_request(self, **params):
        if 'headers' not in params:
            params['headers'] = {}
        params['headers']['X-Vault-Token'] = self.token

        return self.request(**params)
