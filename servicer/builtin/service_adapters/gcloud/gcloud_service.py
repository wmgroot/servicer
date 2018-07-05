from ..base_service import BaseService

class GCloudService(BaseService):
    def __init__(self, config):
        super().__init__(config)
        self.name = 'a-gcloud-service'

    def up(self):
        super().up()

    def down(self):
        super().down()
