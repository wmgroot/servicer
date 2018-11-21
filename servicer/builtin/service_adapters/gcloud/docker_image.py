from ..docker_image import Service as DockerImageService

class Service(DockerImageService):
    def __init__(self, config, logger=None):
        super().__init__(config, logger=logger)

        self.registry = 'us.gcr.io'

    def prune_images(self, older_than='', n_to_keep=0):
        full_path = self.full_image_path(self.config['registry_path'])

        command = "gcloud container images list-tags %s --limit=999999 --sort-by=TIMESTAMP --format='get(digest)'" % full_path

        if older_than:
            command += " --filter=\"timestamp.datetime < '%s'\"" % older_than

        result = self.run(command)
        shas = result['stdout'].strip().split('\n')

        n_to_delete = len(shas)
        if n_to_keep:
            count_result = self.run("gcloud container images list-tags %s --limit=999999 --format='get(digest)' | wc -l" % full_path)
            total_count = int(count_result['stdout'].strip())
            n_to_delete = total_count - n_to_keep

        if n_to_delete > 0:
            self.logger.log('pruning %s image digests from %s' % (n_to_delete, full_path))
            for digest in shas[:n_to_delete]:
                delete_command = 'gcloud container images delete -q --force-delete-tags "%s@%s"' % (full_path, digest)
                result = self.run(delete_command)
