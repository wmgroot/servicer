import os

from servicer.run import run

class BaseService:
    def __init__(self, config=None):
        self.run = run

        if config == None:
            return

        self.config = config

        self.project = os.environ['PROJECT_NAME']
        self.environment = os.getenv('SERVICE_ENVIRONMENT')

    def up(self):
        pass

    def down(self):
        pass
