import os

from servicer.run import run
from servicer.tokens import interpolate_tokens

class BaseService:
    def __init__(self, config=None):
        self.run = run

        if config == None:
            return

        self.config = config

        self.project = os.environ['PROJECT_NAME']
        self.environment = os.getenv('SERVICE_ENVIRONMENT')

        interpolate_tokens(self.config, os.environ)

    def up(self):
        pass

    def down(self):
        pass
