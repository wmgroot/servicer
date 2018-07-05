from ..base_service import BaseService

class AWSService(BaseService):
    def __init__(self, config):
        print(config)
        super().__init__(config)
        self.name = 'an-aws-service'

        import boto3
        self.boto3 = boto3

    def up(self):
        super().up()

    def down(self):
        super().down()
