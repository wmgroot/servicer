import os

from servicer.tokens import interpolate_tokens

class BaseAuthAdapter():

    def __init__(self, config):
        self.config = config
        interpolate_tokens(self.config, os.environ)

    def authenticate(self):
        pass

    def current_user(self):
        pass
