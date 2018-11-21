from ..service import Service as BaseService

class AWSService(BaseService):
    def __init__(self, config, logger=None):
        super().__init__(config, logger=logger)
        self.name = 'an-aws-service'

        import boto3
        self.boto3 = boto3

    def up(self):
        super().up()

    def down(self):
        super().down()
