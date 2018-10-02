from ..docker_image import Service as DockerImageService

class Service(DockerImageService):
    def __init__(self, config):
        super().__init__(config)
        self.registry = 'us.gcr.io'
