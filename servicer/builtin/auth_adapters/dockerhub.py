from .base_auth_adapter import BaseAuthAdapter

import os
from servicer.run import run

class AuthAdapter(BaseAuthAdapter):
    def __init__(self, config):
        super().__init__(config)
        self.run = run

    def authenticate(self):
        self.run('echo "$DOCKER_PASSWORD" | docker login -u "$DOCKER_USERNAME" --password-stdin')
