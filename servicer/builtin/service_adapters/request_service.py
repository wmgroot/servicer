import requests
import json

from .service import Service as BaseService

class Service(BaseService):
    def request(self, **params):
        raise_for_status = params.pop('raise_for_status', True)
        method = params.pop('method', 'get')
        url = params.pop('url')

        if getattr(self, 'base_url'):
            url = '%s/%s' % (self.base_url, url)

        response = getattr(requests, method)(url, **params)
        if raise_for_status:
            response.raise_for_status()
        return response
