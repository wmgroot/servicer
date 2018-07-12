import os
import re
from servicer.run import run

class BaseService:
    def __init__(self, config=None):
        self.run = run

        if config == None:
            return

        self.config = config
        self.interpolate_params(self.config, os.environ)

        self.project = os.environ['PROJECT_NAME']
        self.environment = os.getenv('SERVICE_ENVIRONMENT')

    def up(self):
        pass

    def down(self):
        pass

    def interpolate_params(self, config, params):
        if isinstance(config, dict):
            for key, value in config.items():
                if isinstance(value, str):
                    config[key] = self.replace_tokens(value, params)
                else:
                    self.interpolate_params(value, params)
        elif isinstance(config, list):
            for i in range(len(config)):
                if isinstance(config[i], str):
                    config[i] = self.replace_tokens(config[i], params)
                else:
                    self.interpolate_params(config[i], params)

    def replace_tokens(self, value, params):
        for match in re.findall(r'\${.+?}', value):
            key = match[2:-1]
            value = re.sub(r'\${%s}' % key, params[key], value)

        return value
