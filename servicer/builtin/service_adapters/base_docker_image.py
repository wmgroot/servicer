import os
from .base_service import BaseService

class DockerImageService(BaseService):
    def up(self):
        super().up()

        registry = self.registry

        if 'pull' in self.config:
            for image in self.config['pull']:
                self.pull_image(image)

        image_name = self.build_image()

        tags = ['latest']
        if 'BRANCH' in os.environ:
            tags.append(os.environ['BRANCH'])
        if 'tags' in self.config:
            tags.extend(self.config['tags'])

        for tag in tags:
            tag = tag.replace('/', '.')
            print('pushing tag: %s' % tag)
            full_path = '"%s/%s:%s"' % (registry, self.config['registry_path'], tag)
            self.run('docker tag %s %s' % (image_name, full_path))
            self.run('docker push %s' % full_path)

    def pull_image(self, image_name):
        self.run('docker pull %s' % image_name)

    def build_image(self):
        image_name = self.config['build']['tag']

        build_command = 'docker build -t %s' % image_name
        if 'dockerfile' in self.config['build']:
            build_command = '%s -f %s' % (build_command, self.config['build']['dockerfile'])

        path = '.'
        if 'path' in self.config['build']:
            path = self.config['build']['path']
        build_command = '%s %s' % (build_command, path)

        self.run(build_command)
        return image_name

    def down(self):
        super().down()
