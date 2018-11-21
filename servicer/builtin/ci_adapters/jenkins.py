import textwrap

from .base_ci_adapter import BaseCIAdapter

class CIAdapter(BaseCIAdapter):

    def __init__(self, logger=None):
        super().__init__(logger=logger)

        # https://wiki.jenkins.io/display/JENKINS/Building+a+software+project
        self.env_map['BRANCH_NAME'] = 'BRANCH'
        self.env_map['BUILD_DISPLAY_NAME'] = 'BUILD_NAME'
        self.env_map['BUILD_ID'] = 'BUILD_ID'
        self.env_map['BUILD_NUMBER'] = 'BUILD_NUMBER'
        self.env_map['BUILD_TAG'] = 'TAG'
        self.env_map['BUILD_URL'] = 'BUILD_URL'
        self.env_map['CHANGE_AUTHOR'] = 'PR_USERNAME'
        self.env_map['CHANGE_AUTHOR_DISPLAY_NAME'] = 'PR_AUTHOR_NAME'
        self.env_map['CHANGE_AUTHOR_EMAIL'] = 'PR_AUTHOR_EMAIL'
        self.env_map['CHANGE_ID'] = 'PR_NUMBER'
        self.env_map['CHANGE_TARGET'] = 'PR_TARGET'
        self.env_map['CHANGE_TITLE'] = 'PR_TITLE'
        self.env_map['CHANGE_URL'] = 'PR_URL'
        self.env_map['EXECUTOR_NUMBER'] = 'NODE_INDEX'
        self.env_map['GIT_BRANCH'] = 'BRANCH'
        self.env_map['GIT_COMMIT'] = 'COMMIT'
        self.env_map['GIT_URL'] = 'REPO_URL'
        self.env_map['JENKINS_HOME'] = 'HOME'
        self.env_map['JENKINS_URL'] = 'CI_URL'
        self.env_map['JOB_BASE_NAME'] = 'JOB_BASE_NAME'
        self.env_map['JOB_NAME'] = 'JOB_NAME'
        self.env_map['JOB_URL'] = 'JOB_URL'
        self.env_map['NODE_LABELS'] = 'NODE_LABELS'
        self.env_map['NODE_NAME'] = 'NODE_NAME'
        self.env_map['WORKSPACE'] = 'WORKING_DIRECTORY'

    def generate_ci_config(self, config, service_step_order, path='./Jenkinsfile'):

        self.config = config
        self.indent_value = ' ' * self.config['ci'].get('indent_value', 2)

        servicer_body = [
            """checkout scm

servicer_image = '%s'
sh "docker pull $servicer_image"

""" % self.config['ci'].get('image', 'wmgroot/servicer-alpine'),
            {
                'block': [{
                    'function_name': [
                        'docker.image',
                        'inside',
                    ],
                    'params': [
                        'servicer_image',
                        "'-u root -v /var/run/docker.sock:/var/run/docker.sock -v /home/svc-jenkins/.ssh:/home/root/.ssh'",
                    ],
                    'body': self.servicer_commands(service_step_order),
                    'quote_strings': False,
                }],
            },
        ]

        if 'credentials' in self.config['ci']:
            wrap = '[\n%s%s\n]' % (self.indent_value, '%s')
            servicer_body = {
                'block': [{
                    'function_name': 'withCredentials',
                    'params': self.config['ci']['credentials'],
                    'wrap': wrap,
                    'body': servicer_body,
                }],
            }

        jenkins_body = {
            'block': [{
                'function_name': 'timeout',
                'params': {
                    'time': self.config['ci'].get('timeout', 2),
                    'unit': self.config['ci'].get('timeout_unit', 'HOURS'),
                },
                'body': {
                    'block': [{
                        'function_name': 'node',
                        'params': self.config['ci']['node'],
                        'body': {
                            'block': [{
                                'function_name': 'stage',
                                'params': 'Servicer',
                                'body': servicer_body,
                            }],
                        },
                    }],
                },
            }],
        }

        text = self.evaluate_body(jenkins_body)
        self.write_file(path, text)

    def servicer_commands(self, service_step_order):
        self.logger.log(service_step_order, level='debug')

        commands = ["\nsh 'gcloud auth activate-service-account --key-file=${GOOGLE_APPLICATION_CREDENTIALS}'"]

        for parallel_set in service_step_order:
            params = {}
            for service_step in parallel_set:
                pieces = service_step.split(':')
                command = "sh 'servicer --service=%s --step=%s --ignore_dependencies --no_tag'" % (pieces[0], pieces[1])
                params["'%s'" % service_step] = '{\n%s\n}' % textwrap.indent(self.block('stage', service_step, command), self.indent_value)

            commands.append('\n\n' + self.function_header(
                function_name='parallel',
                params=params,
                indent_params=True,
                quote_strings=False,
            ))

        return commands

    def evaluate_body(self, body):
        text = ''

        if isinstance(body, dict):
            for key, value in body.items():
                if hasattr(self, key):
                    for v in value:
                        if 'body' in v:
                            if not isinstance(v['body'], list):
                                v['body'] = [v['body']]

                            evaluated = ''

                            for b in v['body']:
                                if isinstance(b, dict):
                                    evaluated += self.evaluate_body(b)
                                else:
                                    evaluated += b

                            v['body'] = evaluated

                        result = getattr(self, key)(**v)
                        text += result

        return text

    def block(self, function_name, params={}, body='', wrap='%s', quote_strings=True):
        if not isinstance(function_name, list):
            function_name = [function_name]
            params = [params]

        i = 0
        headers = []
        while i < len(function_name):
            fn = function_name[0]
            headers.append(self.function_header(
                function_name[i],
                params[i],
                wrap=wrap,
                quote_strings=quote_strings,
            ))
            i += 1

        indented_body = textwrap.indent(body, self.indent_value)

        return """%s {
%s
}""" % ('.'.join(headers), indented_body)

    def function_header(
        self,
        function_name,
        params={},
        wrap='%s',
        joiner=', \n    ',
        indent_params=False,
        quote_strings=True,
    ):
        if not isinstance(params, list):
            params = [params]

        joined = []
        for p in params:
            if isinstance(p, dict):
                params_strings = []
                for key, value in p.items():
                    result = ''
                    if hasattr(self, key):
                        result = getattr(self, key)(**value)
                    elif isinstance(value, str) and quote_strings:
                        result = '%s: \'%s\'' % (key, value)
                    else:
                        result = '%s: %s' % (key, value)
                    params_strings.append(result)

                param_end = ',\n' if indent_params else ', '
                joined.append(param_end.join(params_strings))
            else:
                if not isinstance(params, list):
                    params = [params]
                params = ['\'%s\'' % p if isinstance(p, str) and quote_strings else p for p in params]
                joined.append(', '.join(params))

        wrapped = wrap % joiner.join(joined)

        if indent_params:
            wrapped = '\n%s\n' % textwrap.indent(wrapped, self.indent_value)

        return '%s(%s)' % (function_name, wrapped)

    def param_list(self, params={}, wrap='[%s]'):
        params_strings = []
        for key, value in params.items():
            result = ''
            if isinstance(value, str):
                result = '%s: \'%s\'' % (key, value)
            else:
                result = '%s: %s' % (key, value)
            params_strings.append(result)

        return wrap % ', '.join(params_strings)
