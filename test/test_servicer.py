from unittest import TestCase, mock
import os
from datetime import datetime

from servicer.servicer import Servicer

class ServicerTest(TestCase):
    def setUp(self):
        self.servicer = Servicer(args={}, init=False)

        self.servicer.run = mock.Mock()
        self.servicer.logger = mock.Mock()
        self.servicer.token_interpolator = mock.Mock()
        self.servicer.token_interpolator.interpolate_tokens = mock.Mock()
        self.servicer.dependency_grapher = mock.Mock()

    def AutoMock(self, **attributes):
        automock = mock.Mock(spec=attributes.keys())
        for k, v in attributes.items():
            setattr(automock, k, v)
        return automock

class ServicerClassTest(ServicerTest):
    def test_initialized(self):
        pass

class LoadEnvironmentTest(ServicerTest):
    def setUp(self):
        super().setUp()

        self.servicer.datetime = self.AutoMock(
            now=mock.Mock(return_value=self.AutoMock(strftime=mock.Mock(return_value='1970-01-01'))),
            utcnow=mock.Mock(return_value='1970-01-01 00:00:00'),
        )
        self.servicer.load_env_file = mock.Mock(return_value=None)

        self.args = {}

    def test_environment_variables_set(self):
        os.environ['PWD'] = 'project_path'
        result = self.servicer.load_environment(self.args)
        self.assertEqual(os.environ['PROJECT_PATH'], 'project_path')
        self.assertEqual(os.environ['BUILD_DATETIME'], '1970-01-01 00:00:00')
        self.assertEqual(os.environ['BUILD_DATE'], '1970-01-01')

    def test_no_env_file_paths(self):
        result = self.servicer.load_environment(self.args)
        self.servicer.load_env_file.assert_not_called()

    def test_multiple_env_file_paths(self):
        self.args['env_file_paths'] = 'path/one:path/two'
        result = self.servicer.load_environment(self.args)
        self.servicer.load_env_file.assert_has_calls([
            mock.call('path/one'),
            mock.call('path/two'),
        ])

class LoadEnvFileTest(ServicerTest):
    def setUp(self):
        super().setUp()

    def test_path_does_not_exist(self):
        with mock.patch('builtins.open', create=True) as mock_open:
            result = self.servicer.load_env_file('fake/path.yaml')
            mock_open.assert_not_called()

    def test_valid_env_file_path(self):
        with mock.patch('ruamel.yaml.load', create=True) as mock_yaml_load:
            with mock.patch('builtins.open', create=True) as mock_open:
                with mock.patch('os.path.exists', create=True) as mock_os_path_exists:
                    mock_yaml_load.return_value = {'FOO': 'BAR'}
                    mock_os_path_exists.return_value = True

                    result = self.servicer.load_env_file('real/path.yaml')
                    self.assertEqual(os.environ['FOO'], 'BAR')

class GetServiceEnvironmentTest(ServicerTest):
    def setUp(self):
        super().setUp()

        self.servicer.map_service_environment = mock.Mock(return_value=(None, None))

        self.servicer.config = {}
        self.servicer.config['environment'] = {
            'mappings': [{ 'branch': 'foo', 'environment': 'bar' }],
            'formatter': {
                'replace': [
                    { 'from': ['/', '_'], 'to': '-' },
                ],
            },
        }

    def test_custom_mappings(self):
        result = self.servicer.get_service_environment('my-branch', 'my-tag')
        self.servicer.map_service_environment.assert_called_with('my-branch', self.servicer.config['environment']['mappings'], 'my-tag')
        self.assertEqual(result, None)

    def test_matched_environment(self):
        self.servicer.map_service_environment.return_value = ('my_wacky/environment', { 'branch': 'my_wacky/environment' })

        result = self.servicer.get_service_environment('my-branch', 'my-tag')
        self.servicer.map_service_environment.assert_called_with('my-branch', mock.ANY, 'my-tag')
        self.assertEqual(result, 'my-wacky-environment')

class MapServiceEnvironmentTest(ServicerTest):
    def test_no_mappings(self):
        result = self.servicer.map_service_environment('my-branch', [])
        self.assertEqual(result, (None, None))

    def test_branch_mapping(self):
        mapping = { 'branch': 'develop' }
        result = self.servicer.map_service_environment('develop', [mapping])
        self.assertEqual(result, ('develop', mapping))

    def test_branch_environment_mapping(self):
        mapping = { 'branch': 'master', 'environment': 'production' }
        result = self.servicer.map_service_environment('master', [mapping])
        self.assertEqual(result, ('production', mapping))

    def test_branch_wildcard_mapping(self):
        mapping = { 'branch': 'env-*' }
        result = self.servicer.map_service_environment('env-my-branch', [mapping])
        self.assertEqual(result, ('env-my-branch', mapping))

    def test_regex_mapping(self):
        mapping = { 'branch': '/.*-my-.*/' }
        result = self.servicer.map_service_environment('env-my-branch', [mapping])
        self.assertEqual(result, ('env-my-branch', mapping))

    def test_no_match(self):
        result = self.servicer.map_service_environment('my-branch', [
            { 'branch': 'master', 'environment': 'production' },
            { 'branch': 'develop' },
            { 'branch': 'env-*' },
        ])
        self.assertEqual(result, (None, None))

    def test_no_match_but_starts_with_branch(self):
        result = self.servicer.map_service_environment('master_branch', [
            { 'branch': 'master', 'environment': 'production' },
            { 'branch': 'develop' },
            { 'branch': 'env-*' },
        ])
        self.assertEqual(result, (None, None))

    def test_multiple_match(self):
        result = self.servicer.map_service_environment('env-my-branch-qa', [
            { 'branch': 'master', 'environment': 'production' },
            { 'branch': '*-qa', 'environment': 'qa' },
            { 'branch': 'env-*' },
        ])
        self.assertEqual(result, ('qa', { 'branch': '*-qa', 'environment': 'qa' }))

    def test_tag_match(self):
        result = self.servicer.map_service_environment('env-my-branch-qa', [
            { 'tag': 'foo', 'environment': 'production' },
        ], 'foo')
        self.assertEqual(result, ('production', { 'tag': 'foo', 'environment': 'production' }))

    def test_multiple_match_single_mapping(self):
        result = self.servicer.map_service_environment('env-my-branch-qa', [{
            'tag': [
                'foo',
                'bar',
                'baz',
            ],
            'environment': 'production',
        }], 'bar')
        self.assertEqual(result, ('production', { 'tag': ['foo', 'bar', 'baz'], 'environment': 'production' }))

class RunServiceStepTest(ServicerTest):
    def setUp(self):
        super().setUp()

        self.servicer.config = {
            'args': {}
        }

        self.adapter = mock.Mock()
        self.adapter.up = mock.Mock(return_value='service-step results')
        self.Service = mock.Mock(return_value=self.adapter)
        self.module = self.AutoMock(Service=self.Service)

        def mock_load_service_module(service):
            service['module'] = self.module

        self.servicer.load_service_module = mock.Mock(side_effect=mock_load_service_module)
        self.servicer.run_commands = mock.Mock()

        self.service = {
            'module': self.module,
            'name': 'service_1',
            'steps': {
                'build': {'config': {}},
            }
        }

    def test_runs_an_empty_service_step(self):
        self.service.pop('module')
        self.service['steps']['build'].pop('config')

        result = self.servicer.run_service_step(self.service, self.service['steps']['build'])

        self.assertEqual(self.servicer.run_commands.mock_calls, [
            mock.call(None),
            mock.call(None),
        ])
        self.servicer.token_interpolator.interpolate_tokens.assert_not_called()

    def test_runs_a_service_step_with_config_and_no_module(self):
        self.service.pop('module')
        os.environ = {}

        result = self.servicer.run_service_step(self.service, self.service['steps']['build'])

        self.servicer.load_service_module.assert_called_with(self.service)

        self.assertEqual(self.servicer.run_commands.mock_calls, [
            mock.call(None),
            mock.call(None),
        ])
        self.servicer.token_interpolator.interpolate_tokens.assert_called_with({}, self.servicer.config)
        self.assertEqual(self.service['steps']['build']['results'], 'service-step results')

    def test_runs_a_service_step_with_module_and_no_config(self):
        self.service['steps']['build'].pop('config')

        result = self.servicer.run_service_step(self.service, self.service['steps']['build'])

        self.assertEqual(self.servicer.run_commands.mock_calls, [
            mock.call(None),
            mock.call(None),
        ])
        self.servicer.token_interpolator.interpolate_tokens.assert_not_called()

    def test_runs_a_service_step_with_module_and_config(self):
        os.environ = {}
        result = self.servicer.run_service_step(self.service, self.service['steps']['build'])

        self.assertEqual(self.servicer.run_commands.mock_calls, [
            mock.call(None),
            mock.call(None),
        ])
        self.servicer.token_interpolator.interpolate_tokens.assert_called_with({}, self.servicer.config)

        self.assertTrue('git' not in self.service['steps']['build']['config'])
        self.assertEqual(self.service['steps']['build']['results'], 'service-step results')

    def test_runs_a_service_step_with_git_integration(self):
        self.servicer.config['git'] = {'enabled': True}
        self.servicer.git = {}
        os.environ = {}

        result = self.servicer.run_service_step(self.service, self.service['steps']['build'])

        self.assertEqual(self.servicer.run_commands.mock_calls, [
            mock.call(None),
            mock.call(None),
        ])
        self.servicer.token_interpolator.interpolate_tokens.assert_called_with({'git': {'module': {}}}, self.servicer.config)

        self.assertEqual(self.service['steps']['build']['config']['git'], {'module': {}})
        self.assertEqual(self.service['steps']['build']['results'], 'service-step results')

    def test_runs_a_service_step_with_commands(self):
        self.service['steps']['build']['commands'] = [
            'pre-command1.sh',
            'rm -rf treeeeee xD',
        ]
        self.service['steps']['build']['post_commands'] = [
            'cowsay moo',
            'yes | lolcat',
        ]

        result = self.servicer.run_service_step(self.service, self.service['steps']['build'])

        self.assertEqual(self.servicer.run_commands.mock_calls, [
            mock.call(['pre-command1.sh', 'rm -rf treeeeee xD']),
            mock.call(['cowsay moo', 'yes | lolcat']),
        ])

class BlobRegexMatchTest(ServicerTest):
    def test_matches_same_words(self):
        result = self.servicer.glob_regex_match('pen', 'pen')
        self.assertEqual(result.group(0), 'pen')

    def test_does_not_match_different_words(self):
        result = self.servicer.glob_regex_match('apple', 'pineapple')
        self.assertEqual(result, None)

    def test_matches_outside_globs(self):
        result = self.servicer.glob_regex_match('*apple', 'pineapple')
        self.assertEqual(result.group(0), 'pineapple')

    def test_matches_inside_globs(self):
        result = self.servicer.glob_regex_match('pen*apple', 'penpineapple')
        self.assertEqual(result.group(0), 'penpineapple')

    def test_matches_many_globs(self):
        result = self.servicer.glob_regex_match('*appleapple*', 'penpineappleapplepen')
        self.assertEqual(result.group(0), 'penpineappleapplepen')

    def test_handles_globs_with_regex_metacharacters(self):
        result = self.servicer.glob_regex_match('*.*.*', 'apple')
        self.assertEqual(result, None)

    def test_fails_globs(self):
        result = self.servicer.glob_regex_match('*appleapple*', 'penpineapplepen')
        self.assertEqual(result, None)

    def test_matches_regexes(self):
        result = self.servicer.glob_regex_match('/\w+\d+three/', 'one2three')
        self.assertEqual(result.group(0), 'one2three')

    def test_fails_regexes(self):
        result = self.servicer.glob_regex_match('/\w+\d+three/', 'onethree')
        self.assertEqual(result, None)

    def test_matches_any(self):
        result = self.servicer.glob_regex_match(['apple', 'pen*apple'], 'penpineapple')
        self.assertEqual(result.group(0), 'penpineapple')

    def test_matches_nothing(self):
        result = self.servicer.glob_regex_match(['apple', 'pineapple'], 'penpineapple')
        self.assertEqual(result, None)

    def test_matches_nothing(self):
        result = self.servicer.glob_regex_match('apple', None)
        self.assertEqual(result, None)
