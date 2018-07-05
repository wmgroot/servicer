import os

class BaseCIAdapter():

    def __init__(self):
        self.env_map = {}

    def convert_environment_variables(self):
        for key, value in os.environ.items():
            if key in self.env_map:
                os.environ[self.env_map[key]] = value
                os.environ.pop(key)
