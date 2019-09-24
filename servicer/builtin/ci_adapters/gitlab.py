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

        for s, stage in enumerate(service_step_order):
            stage_name = 'stage%s' % s
            data['stages'].append(stage_name)

            for service_step in stage:
                service, step = service_step.split(':')

                data[service_step] = {
                    'stage': stage_name,
                    'script': [
                        'servicer --service=%s --step=%s --ignore_dependencies --no_tag' % (service, step),
                    ],
                }

                if 'ci' in self.config['services'][service] and 'extra_args' in self.config['services'][service]['ci']:
                    data[service_step].update(self.config['services'][service]['ci']['extra_args'])

                if 'ci' in self.config['services'][service]['steps'][step] and 'extra_args' in self.config['services'][service]['steps'][step]['ci']:
                    data[service_step].update(self.config['services'][service]['steps'][step]['ci']['extra_args'])

        if 'extra_args' in self.config['ci']:
            data.update(self.config['ci']['extra_args'])

        text = '\n'.join(['# %s' % line for line in self.auto_gen_header().split('\n')])
        text += '\n'
        text += yaml.dump(data, default_flow_style=False)

        with open(path, "w") as text_file:
            text_file.write(text)

        self.logger.log('CI config file generated: %s' % path)
