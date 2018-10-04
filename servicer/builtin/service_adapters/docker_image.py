import os
from .service import Service as BaseService

class Service(BaseService):
    def __init__(self, config):
        super().__init__(config)
        self.registry = None

    def up(self):
        super().up()

        if 'steps' in self.config:
            self.run_steps(self.config['steps'])

    def run_steps(self, steps):
        for step in steps:
            getattr(self, step['type'])(**step.get('args', {}))

    def pull(self, image_name):
        self.run('docker pull %s' % image_name)

    def build(self, image=None, dockerfile=None, path='.', build_args={}):
        build_command = 'docker build -t %s' % image

        if dockerfile:
            build_command = '%s -f %s' % (build_command, dockerfile)

        if build_args:
            for key, value in build_args.items():
                build_command = '%s --build-arg %s=%s' % (build_command, key, value)

        build_command = '%s %s' % (build_command, path)

        self.run(build_command)

    def push(self, image=None, tags=[]):
        if 'latest' not in tags:
            tags.insert(0, 'latest')

        tags = [t.replace('/', '.') for t in tags]

        self.tag(image=image, tags=tags)

        for tag in tags:
            full_path = self.full_image_path(self.config['registry_path'], tag)
            self.run('docker push %s' % full_path)

    def tag(self, image=None, tags=[]):
        for tag in tags:
            full_path = self.full_image_path(self.config['registry_path'], tag)
            self.run('docker tag %s %s' % (image, full_path))

    def full_image_path(self, registry_path, tag):
        full_path = '%s:%s' % (registry_path, tag)
        if self.registry:
            full_path = '%s/%s' % (self.registry, full_path)
        return '"%s"' % full_path
