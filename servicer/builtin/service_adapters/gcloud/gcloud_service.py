from ..service import Service as BaseService

class GCloudService(BaseService):
    def __init__(self, config, logger=None):
        super().__init__(config, logger=logger)
        self.name = 'a-gcloud-service'

    def up(self):
        super().up()

    def down(self):
        super().down()
