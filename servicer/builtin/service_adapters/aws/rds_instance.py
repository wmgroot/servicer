from .aws_service import AWSService
import time
import json

class Service(AWSService):
    def up(self):
        super().up()

        self.rds = self.boto3.client('rds')

        self.create_db_instance(self.config['rds_params'])
        database_host = self.wait_for_db_available(self.config['rds_params']['DBInstanceIdentifier'])

        return {
            'database_host': database_host,
        }

    def create_db_instance(self, params):
        from botocore.client import ClientError

        try:
            self.rds.create_db_instance(**params)
            print('creating RDS instance with ID: %s' % params['DBInstanceIdentifier'])
        except ClientError as e:
            if 'DBInstanceAlreadyExists' in str(e):
                print('DB instance (%s) exists already, continuing to poll ...' % id)
            else:
                raise

    def wait_for_db_available(self, id, attempts=120, sleep_time=10):
        instance = self.get_instance(id)
        while instance['DBInstanceStatus'] != 'available' and attempts > 0:
            time.sleep(sleep_time)
            instance = self.get_instance(id)
            attempts -= 1
            print('status: %s, remaining attempts: %s' % (instance['DBInstanceStatus'], attempts))

        print('DB instance (%s) ready at: %s' % (id, instance['Endpoint']['Address']))
        return instance['Endpoint']['Address']

    def get_instance(self, id):
        response = self.rds.describe_db_instances(DBInstanceIdentifier=id)
        return response['DBInstances'][0]

    def down():
        print('TODO!')
