from ..base_docker_image import DockerImageService

class Service(DockerImageService):
    def __init__(self, config):
        super().__init__(config)
        self.registry = 'us.gcr.io'

    # def run(self, command):
    #     auth_script = self.config['initialized_provider']['auth_script_path']
    #     command = '%s && %s' % (auth_script, command)
    #     super().run(command, shell=False)
