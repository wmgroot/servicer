import glob
import os

from .service import Service as BaseService

class Service(BaseService):
    def up(self):
        super().up()

        if 'tasks' in self.config:
            self.run_tasks(self.config['tasks'])

    def run_tasks(self, tasks):
        for task in tasks:
            getattr(self, task['type'])(**task['args'])

    def interpolate_file(self, files=[], ignore_missing_key=False):
        if not isinstance(files, list):
            files = [files]

        for f in files:
            if 'output' not in f:
                f['output'] = f['input']

            input_files = glob.glob(f['input'])
            for i in input_files:
                output_path = f['output']
                if output_path.endswith('/'):
                    output_path = '%s%s' % (output_path, os.path.basename(i))

                self.logger.log('interpolating tokens (%s -> %s)' % (i, output_path))

                data = None
                with open(i, 'r') as in_file:
                    data = in_file.read()

                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                with open(output_path, 'w') as out_file:
                    params = {**os.environ, **self.full_config}
                    data = self.token_interpolator.replace_tokens(data, params=params, ignore_missing_key=ignore_missing_key)
                    out_file.write(data)
