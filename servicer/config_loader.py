import os
import json
import yaml

from .token_interpolator import TokenInterpolator

class ConfigLoader():
    def __init__(self, args={}):
        self.args = args
        self.token_interpolator = TokenInterpolator()
        self.module_path = os.path.dirname(os.path.realpath(globals()['__file__']))
        self.servicer_config_path = args.get('servicer_config_path')
        self.servicer_config_file_path = '%s/%s' % (self.servicer_config_path, args.get('services_file'))

    def load_config(self):
        services_config = {}

        if self.servicer_config_path and self.servicer_config_file_path:
            print('loading services config from (%s)' % self.servicer_config_file_path)
            self.load_extended_config(config_path=self.servicer_config_file_path, config=services_config)
            services_config = self.merge_defaults(config=services_config)
            self.merge_included_configs(config_path=self.servicer_config_file_path, config=services_config)

            services_config['config_path'] = self.servicer_config_path

        services_config['module_path'] = self.module_path
        services_config['args'] = self.args

        if 'environment' in services_config and 'variables' in services_config['environment']:
            self.load_environment_variables(services_config['environment']['variables'])

        return services_config

    # recursively load configs, overwriting base config values
    def load_extended_config(self, config_path=None, config=None):
        merge_config = yaml.load(open(config_path))

        if 'extends' in merge_config:
            config_path_pieces = config_path.split('/')
            inherit_path = '%s/%s' % ('/'.join(config_path_pieces[:-1]), merge_config.pop('extends'))
            print('Extending: %s' % inherit_path)
            self.load_extended_config(config_path=inherit_path, config=config)

        self.merge_config(config, merge_config)

    def merge_included_configs(self, config_path=None, config=None):
        iterable = None

        if isinstance(config, dict):
            self.load_include_configs(config_path=config_path, config=config)
            iterable = config.values()
        elif isinstance(config, list):
            iterable = config

        if iterable:
            for value in iterable:
                self.merge_included_configs(config_path=config_path, config=value)

    def load_include_configs(self, config_path=None, config=None):
        if 'includes' not in config:
            return

        includes = config.pop('includes')
        if not isinstance(includes, list):
            includes = [includes]

        for include in includes:
            path = include
            params = {}

            if isinstance(include, dict):
                path = include['path']
                params = include['params']

            config_path_pieces = config_path.split('/')
            include_path = '%s/%s' % ('/'.join(config_path_pieces[:-1]), path)

            print('Including: %s' % include_path)

            include_config = {}
            self.load_extended_config(config_path=include_path, config=include_config)
            self.merge_included_configs(config_path=self.servicer_config_file_path, config=include_config)

            if params:
                self.token_interpolator.interpolate_tokens(include_config, params, ignore_missing_key=True)

            self.merge_config(config, include_config)

    def merge_defaults(self, config={}):
        default_config_path = '%s/builtin/defaults.yaml' % self.module_path
        default_config = yaml.load(open(default_config_path))
        self.merge_config(default_config, config)

        return default_config

    def merge_config(self, merge_to, merge_from):
        for key, value in merge_from.items():
            if isinstance(value, dict):
                # get node or create one
                node = merge_to.setdefault(key, {})
                self.merge_config(node, value)
            else:
                merge_to[key] = value

        return merge_to

    def interpolate_config(self, config):
        print('Interpolating Tokens...')
        self.token_interpolator.interpolate_tokens(config, os.environ, ignore_missing_key=True)

    def load_environment_variables(self, variables={}):
        for key, value in variables.items():
            os.environ[key] = self.token_interpolator.replace_tokens(value, os.environ)
