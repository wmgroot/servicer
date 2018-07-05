import os
import subprocess
import re

class BaseService:
    def __init__(self, config=None):
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

    def run(self, command, check=True, shell=True):
        print('executing: %s' % command)

        try:
            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=check,
                shell=shell,
            )
            # result = subprocess.run(command, check = check, shell = shell)
            print(result.stdout.decode('utf-8'))
        except subprocess.CalledProcessError as e:
            print('failed: %s' % e.returncode)
            print(e.output.decode('utf-8'))
            raise
