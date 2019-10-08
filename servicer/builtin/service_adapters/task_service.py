import glob
import os
import json
from ruamel import yaml

from .service import Service as BaseService

class Service(BaseService):
    def up(self):
        super().up()

        if 'tasks' in self.config:
            self.run_tasks(self.config['tasks'])

    def run_tasks(self, tasks):
        for task in tasks:
            args = task.get('args', {})
            getattr(self, task['type'])(**args)

    def dig(self, data, path):
        keys = path.split('.')
        while keys:
            if keys[0].isdigit():
                keys[0] = int(keys[0])

            if keys[0]:
                data = data[keys[0]]

            keys.pop(0)

        return data

    def write_config_to_file(self, file_path, config_path='', file_type='yaml'):
        self.logger.log('writing file from config: (%s -> %s)' % (config_path, file_path))

        local_config_prefix = 'self.'
        if config_path.startswith(local_config_prefix):
            self_config_path = config_path[len(local_config_prefix):]
            config = self.dig(self.config, self_config_path)
        else:
            config = self.dig(self.full_config, config_path)

        self.logger.log(json.dumps(config, indent=2, default=str), level='debug')

        if file_type not in ['json', 'yaml']:
            self.logger.log('file_type: %s must be one of [yaml, json]' % file_type, level='error')
            exit(1)

        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w') as fp:
            if file_type == 'yaml':
                yaml.dump(config, fp, default_flow_style=False)
            elif file_type == 'json':
                json.dump(config, fp, indent=2)

    def interpolate_file(self, files=[], ignore_missing_key=False, params={}):
        if not isinstance(files, list):
            files = [files]

        for f in files:
            if 'output' not in f:
                f['output'] = f['input']

            if not isinstance(f['output'], list):
                f['output'] = [f['output']]

            input_files = glob.glob(f['input'])
            if not input_files:
                self.logger.log('found no files for input path: %s' % f['input'], level='warn')

            for i in input_files:
                data = None
                with open(i, 'r') as in_file:
                    data = in_file.read()

                for o in f['output']:
                    output_path = o
                    if output_path.endswith('/'):
                        output_path = '%s%s' % (output_path, os.path.basename(i))

                    self.logger.log('interpolating tokens (%s -> %s)' % (i, output_path))

                    os.makedirs(os.path.dirname(output_path), exist_ok=True)
                    with open(output_path, 'w') as out_file:
                        params = {**os.environ, **self.full_config, **params}
                        data = self.token_interpolator.replace_tokens(data, params=params, ignore_missing_key=ignore_missing_key)
                        out_file.write(data)
