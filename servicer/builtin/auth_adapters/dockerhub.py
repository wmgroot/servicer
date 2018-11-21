from .base_auth_adapter import BaseAuthAdapter

import os
from servicer.run import run

class AuthAdapter(BaseAuthAdapter):
    def __init__(self, config, logger=None):
        super().__init__(config, logger=logger)
        self.run = run

    def authenticate(self):
        self.run('echo "$DOCKER_PASSWORD" | docker login -u "$DOCKER_USERNAME" --password-stdin')
