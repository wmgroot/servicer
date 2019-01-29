import os

from servicer.run import run

class Service:
    def __init__(self, config=None, logger=None):
        self.logger = logger
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
