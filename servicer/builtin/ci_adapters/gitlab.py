from .base_ci_adapter import BaseCIAdapter

from ruamel import yaml

class CIAdapter(BaseCIAdapter):

    def __init__(self, logger=None):
        super().__init__(logger=logger)

        # https://docs.gitlab.com/ee/ci/variables/predefined_variables.html
        self.env_map['CI_COMMIT_REF_NAME'] = 'BRANCH'
        self.env_map['CI_PIPELINE_ID'] = 'BUILD_NUMBER'
        self.env_map['CI_PIPELINE_URL'] = 'BUILD_URL'
        self.env_map['CI_JOB_NAME'] = 'JOB_NAME'
        self.env_map['CI_PROJECT_URL'] = 'REPO_URL'
        self.env_map['CI_COMMIT_SHA'] = 'COMMIT'
        self.env_map['CI_COMMIT_TAG'] = 'TAG'
        self.env_map['GITLAB_USER_LOGIN'] = 'USERNAME'
        self.env_map['CI_PROJECT_DIR'] = 'WORKING_DIRECTORY'

    def generate_ci_config(self, config, service_step_order, path='./.gitlab-ci.yml'):

        self.config = config

        data = {
            'stages': [],
        }

        if 'extra_args' in self.config['ci']:
            data.update(self.config['ci']['extra_args'])

        for s, stage in enumerate(service_step_order):
            stage_name = 'stage%s' % s

            if 'gitlab' in self.config['ci'] and 'infer_stage_name' in self.config['ci']['gitlab'] and self.config['ci']['gitlab']['infer_stage_name']:
                _, step = stage[0].split(':')
                stage_name = step

            data['stages'].append(stage_name)

            for service_step in stage:
                service, step = service_step.split(':')

                service_config = self.config['services'][service]
                service_step_config = service_config['steps'][step]

                data[service_step] = {
                    'stage': stage_name,
                    'script': [
                        'servicer --service=%s --step=%s --ignore_dependencies --no_tag' % (service, step),
                    ],
                }

                if 'extra_args' in self.config['ci']:
                    data[service_step].update(self.config['ci']['extra_job_args'])

                if 'commands' in service_step_config and not 'config' in service_step_config:
                    data[service_step]['script'] = self.flatten_commands(service_step_config['commands'])

                if 'gitlab' in self.config['ci'] and 'infer_only' in self.config['ci']['gitlab'] and self.config['ci']['gitlab']['infer_only']:
                    only_list = []
                    if 'service_environment' in service_config:
                        se = service_config['service_environment']
                        if not isinstance(se, list):
                            se = [se]
                        only_list.extend(se)

                    # TODO: pull step config efficiently
                    # if 'config' in self.config['steps'][step] and 'service_environment' in self.config['steps'][step]['config']:
                    #     se = self.config['steps'][step]['config']['service_environment']
                    #     if not isinstance(se, list):
                    #         se = [se]
                    #     only_list.extend(se)

                    if 'service_environment' in service_config:
                        only_list = service_config['service_environment']
                        if not isinstance(only_list, list):
                            only_list = [only_list]

                    if only_list:
                        data[service_step]['only'] = only_list

                if 'ci' in service_config and 'extra_args' in service_config['ci']:
                    data[service_step].update(service_config['ci']['extra_args'])

                if 'ci' in service_step_config and 'extra_args' in service_step_config['ci']:
                    data[service_step].update(service_step_config['ci']['extra_args'])

        text = '\n'.join(['# %s' % line for line in self.auto_gen_header().split('\n')])
        text += '\n'
        text += yaml.dump(data, default_flow_style=False)

        with open(path, "w") as text_file:
            text_file.write(text)

        self.logger.log('CI config file generated: %s' % path)

    def flatten_commands(self, commands):
        flattened_commands = []

        for c in commands:
            if isinstance(c, dict):
                if 'env_var' in c:
                    flattened_commands.append('%s=$(%s)' % (c['env_var'], c['command']))

                if 'commands' in c and 'context' in c:
                    context_commands = c['commands']
                    if 'template' in c['context']:
                        context_commands = [c['context']['template'] % _c for _c in c['commands']]

                    flattened_commands.extend(context_commands)
            else:
                flattened_commands.append(c)

        return flattened_commands
