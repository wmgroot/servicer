import os

class BaseAuthAdapter():

    def __init__(self, config, logger=None):
        self.logger = logger
        self.config = config

    def authenticate(self):
        pass

    def current_user(self):
        pass
