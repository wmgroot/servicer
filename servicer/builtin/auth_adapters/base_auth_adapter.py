import os

class BaseAuthAdapter():

    def __init__(self, config):
        self.config = config

    def authenticate(self):
        pass

    def current_user(self):
        pass
