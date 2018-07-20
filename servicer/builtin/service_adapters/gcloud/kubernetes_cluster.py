from .gcloud_service import GCloudService

import os
import time
import yaml

class Service(GCloudService):
    def up(self):
        super().up()

        self.cluster_name = self.config['cluster_name']

        self.ensure_cluster(self.cluster_name)

        if 'cluster_configs' in self.config:
            for config in self.config['cluster_configs']:
                self.apply(config)

        if 'wait_for_pending' in self.config:
            args = {}
            if isinstance(self.config['wait_for_pending'], dict):
                args = self.config['wait_for_pending']

            self.wait_for_pending(**args)

    def ensure_cluster(self, cluster_name):
        print('ensuring cluster: %s' % cluster_name)
        self.run('gcloud container clusters create %s || true' % cluster_name)
        self.run('gcloud container clusters get-credentials %s' % cluster_name)
        print('cluster ready: %s' % cluster_name)

    def apply(self, config):
        with open('file.yaml', 'w') as outfile:
            yaml.dump(config, outfile, default_flow_style=False)

        self.run('kubectl apply -f file.yaml')
        os.remove('file.yaml')

    def wait_for_pending_services(self, **args):
        max_wait = args.get('max_wait', 300)
        wait_increment = args.get('wait_increment', 5)
        current_wait = 0

        status = '<pending>'
        while True:
            result = self.run('kubectl get service')
            if '<pending>' in result['stdout']:
                print('(%ss) found pending actions for cluster %s, waiting...' % (current_wait, self.cluster_name))
                time.sleep(wait_increment)
                current_wait += wait_increment
            else:
                break

            if current_wait > max_wait:
                print('timed out while waiting for pending actions, terminating')
                sys.exit(1)
