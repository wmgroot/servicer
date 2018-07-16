import os
from .base_service import BaseService

class DockerImageService(BaseService):
    def up(self):
        super().up()

        if 'steps' in self.config:
            self.run_steps(self.config['steps'])

    def run_steps(self, steps):
        for step in steps:
            getattr(self, step['type'])(**step.get('args', {}))

    def pull(self, image_name):
        self.run('docker pull %s' % image_name)

    def build(self, image=None, dockerfile=None, path='.'):
        build_command = 'docker build -t %s' % image

        if dockerfile:
            build_command = '%s -f %s' % (build_command, dockerfile)

        build_command = '%s %s' % (build_command, path)

        self.run(build_command)

    def push(self, image=None, tags=[]):
        if 'latest' not in tags:
            tags.insert(0, 'latest')

        tags = [t.replace('/', '.') for t in tags]

        self.tag(image=image, tags=tags)

        for tag in tags:
            full_path = '"%s/%s:%s"' % (self.registry, self.config['registry_path'], tag)
            self.run('docker push %s' % full_path)

    def tag(self, image=None, tags=[]):
        for tag in tags:
            full_path = '"%s/%s:%s"' % (self.registry, self.config['registry_path'], tag)
            self.run('docker tag %s %s' % (image, full_path))
