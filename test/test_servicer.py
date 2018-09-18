from unittest import TestCase, mock
import os
from datetime import datetime

from servicer.servicer import Servicer

class ServicerTest(TestCase):
    def setUp(self):
        self.servicer = Servicer(args={})

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
        print(self.servicer.load_env_file.mock.calls)
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
        with mock.patch('yaml.load', create=True) as mock_yaml_load:
            with mock.patch('builtins.open', create=True) as mock_open:
                with mock.patch('os.path.exists', create=True) as mock_os_path_exists:
                    mock_yaml_load.return_value = {'FOO': 'BAR'}
                    mock_os_path_exists.return_value = True

                    result = self.servicer.load_env_file('real/path.yaml')
                    self.assertEqual(os.environ['FOO'], 'BAR')

class GetServiceEnvironmentTest(ServicerTest):
    def setUp(self):
        super().setUp()

        self.servicer.map_service_environment = mock.Mock(return_value=None)

        self.servicer.config['environment'] = {
            'mappings': [{ 'branch': 'foo', 'environment': 'bar' }],
        }

    def test_custom_mappings(self):
        result = self.servicer.get_service_environment('my-branch')
        self.servicer.map_service_environment.assert_called_with('my-branch', self.servicer.config['environment']['mappings'])
        self.assertEqual(result, None)

    def test_matched_environment(self):
        self.servicer.map_service_environment.return_value = 'my_wacky/environment'

        result = self.servicer.get_service_environment('my-branch')
        self.servicer.map_service_environment.assert_called_with('my-branch', mock.ANY)
        self.assertEqual(result, 'my-wacky-environment')

class MapServiceEnvironmentTest(ServicerTest):
    def test_no_mappings(self):
        result = self.servicer.map_service_environment('my-branch', [])
        self.assertEqual(result, None)

    def test_branch_mapping(self):
        result = self.servicer.map_service_environment('develop', [
            { 'branch': 'develop' },
        ])
        self.assertEqual(result, 'develop')

    def test_branch_environment_mapping(self):
        result = self.servicer.map_service_environment('master', [
            { 'branch': 'master', 'environment': 'production' },
        ])
        self.assertEqual(result, 'production')

    def test_branch_wildcard_mapping(self):
        result = self.servicer.map_service_environment('env-my-branch', [
            { 'branch': 'env-*' },
        ])
        self.assertEqual(result, 'env-my-branch')

    def test_regex_mapping(self):
        result = self.servicer.map_service_environment('env-my-branch', [
            { 'branch': '/.*-my-.*/' },
        ])
        self.assertEqual(result, 'env-my-branch')

    def test_no_match(self):
        result = self.servicer.map_service_environment('my-branch', [
            { 'branch': 'master', 'environment': 'production' },
            { 'branch': 'develop' },
            { 'branch': 'env-*' },
        ])
        self.assertEqual(result, None)

    def test_no_match_but_starts_with_branch(self):
        result = self.servicer.map_service_environment('master_branch', [
            { 'branch': 'master', 'environment': 'production' },
            { 'branch': 'develop' },
            { 'branch': 'env-*' },
        ])
        self.assertEqual(result, None)

    def test_multiple_match(self):
        result = self.servicer.map_service_environment('env-my-branch-qa', [
            { 'branch': 'master', 'environment': 'production' },
            { 'branch': '*-qa', 'environment': 'qa' },
            { 'branch': 'env-*' },
        ])
        self.assertEqual(result, 'qa')

class OrderServiceStepsTest(ServicerTest):
    def setUp(self):
        super().setUp()

        self.servicer.calculate_service_dependencies = mock.Mock(side_effect=[
            {'service_1:test': set(['service_1:build'])},
            {'service_2:test': set(['service_2:build'])},
        ])
        self.servicer.toposort2 = mock.Mock(return_value=[
            ['service_1:build', 'service_2:build'],
            ['service_1:test', 'service_2:test'],
        ])
        self.servicer.config = {
            'services': {
                'service_1': {
                    'field1': 'value1',
                },
                'service_2': {
                    'field2': 'value2',
                },
            },
        }

    def test_returns_a_service_step_order(self):
        result = self.servicer.order_service_steps(self.servicer.config['services'].keys())

        self.servicer.calculate_service_dependencies.assert_has_calls([
            mock.call(self.servicer.config['services']['service_1']),
            mock.call(self.servicer.config['services']['service_2']),
        ])
        self.servicer.toposort2.assert_called_with({
            'service_1:test': set(['service_1:build']),
            'service_2:test': set(['service_2:build']),
        })
        self.assertEqual(result, [
            ['service_1:build', 'service_2:build'],
            ['service_1:test', 'service_2:test'],
        ])

    def test_returns_an_empty_service_step_order(self):
        self.servicer.toposort2 = mock.Mock(return_value=[])

        result = self.servicer.order_service_steps([])

        self.servicer.calculate_service_dependencies.assert_not_called()
        self.servicer.toposort2.assert_called_with({})
        self.assertEqual(result, [])

class CalculateServiceDependenciesTest(ServicerTest):
    def setUp(self):
        super().setUp()

        self.servicer.add_dependencies = mock.Mock()

        self.servicer.step_order = [
            'build',
            'test',
            'deploy',
        ]

        self.service = {
            'name': 'service_1',
            'steps': {
                'build': {'config': {}},
                'test': {'config': {}},
                'deploy': {'config': {}},
            },
        }

    def test_calculates_standard_step_order(self):
        result = self.servicer.calculate_service_dependencies(self.service)

        self.servicer.add_dependencies.assert_has_calls([
            mock.call({}, self.service, 'test', 'service_1:build', persistent_steps=True),
            mock.call({}, self.service, 'deploy', 'service_1:test', persistent_steps=True),
        ])
        self.assertEqual(result, {})

    def test_ignores_steps_that_does_not_exist(self):
        self.service['steps']['bad_step'] = {'config': {}}

        result = self.servicer.calculate_service_dependencies(self.service)

        self.servicer.add_dependencies.assert_has_calls([
            mock.call({}, self.service, 'test', 'service_1:build', persistent_steps=True),
            mock.call({}, self.service, 'deploy', 'service_1:test', persistent_steps=True),
        ])
        self.assertEqual(result, {})

    def test_calculates_custom_service_dependencies(self):
        self.service['depends_on'] = [
            'service_2',
        ]

        result = self.servicer.calculate_service_dependencies(self.service)

        self.servicer.add_dependencies.assert_has_calls([
            mock.call({}, self.service, 'build', ['service_2']),
            mock.call({}, self.service, 'test', 'service_1:build', persistent_steps=True),
            mock.call({}, self.service, 'test', ['service_2']),
            mock.call({}, self.service, 'deploy', 'service_1:test', persistent_steps=True),
            mock.call({}, self.service, 'deploy', ['service_2']),
        ])
        self.assertEqual(result, {})

    def test_calculates_custom_step_dependencies(self):
        self.service['steps']['test']['depends_on'] = [
            'service_2',
            'service_3:build',
        ]

        result = self.servicer.calculate_service_dependencies(self.service)

        self.servicer.add_dependencies.assert_has_calls([
            mock.call({}, self.service, 'test', 'service_1:build', persistent_steps=True),
            mock.call({}, self.service, 'test', ['service_2', 'service_3:build']),
            mock.call({}, self.service, 'deploy', 'service_1:test', persistent_steps=True),
        ])
        self.assertEqual(result, {})

class AddDependenciesTest(ServicerTest):
    def setUp(self):
        super().setUp()

        self.servicer.config = {
            'services': {
                'service_1': {
                    'name': 'service_1',
                    'steps': {'build': {}, 'test': {}},
                },
                'service_2': {
                    'name': 'service_2',
                    'steps': {'build': {}, 'test': {}},
                },
                'service_3': {
                    'name': 'service_3',
                    'steps': {'build': {}, 'test': {}},
                },
            },
        }

        self.servicer.steps = {
            'build': {'name': 'build'},
            'test': {'name': 'test'},
            'deploy': {
                'name': 'deploy',
                'config': {'persists': True},
            },
        }

        self.servicer.active_services = self.servicer.config['services'].keys()

        self.service = {
            'name': 'service_1',
            'steps': {
                'build': {'config': {}},
                'test': {'config': {}},
                'deploy': {'config': {}},
            },
        }
        self.dependencies = {}

    def test_adds_a_single_service_step_dependency(self):
        result = self.servicer.add_dependencies(self.dependencies, self.service, 'build', 'service_2:build')

        self.assertEqual(self.dependencies, {
            'service_1:build': set(['service_2:build']),
        })

    def test_adds_a_list_of_service_dependencies(self):
        result = self.servicer.add_dependencies(self.dependencies, self.service, 'test', ['service_2', 'service_3'])

        self.assertEqual(self.dependencies, {
            'service_1:test': set(['service_2:test', 'service_3:test']),
        })

    def test_adding_a_service_name_wildcard(self):
        result = self.servicer.add_dependencies(self.dependencies, self.service, 'test', ['*:test'])

        self.assertEqual(self.dependencies, {
            'service_1:test': set(['service_1:test', 'service_2:test', 'service_3:test']),
        })

    def test_adds_a_list_of_service_step_dependencies(self):
        result = self.servicer.add_dependencies(self.dependencies, self.service, 'deploy', [
            'service_2:build',
            'service_3:test',
        ])

        self.assertEqual(self.dependencies, {
            'service_1:deploy': set(['service_2:build', 'service_3:test']),
        })

    def test_skips_persists_steps_by_default(self):
        result = self.servicer.add_dependencies(self.dependencies, self.service, 'deploy', [
            'service_2',
            'service_3:deploy',
        ])

        self.assertEqual(self.dependencies, {
            'service_1:deploy': set(),
        })

    def test_does_not_skips_a_persists_step(self):
        result = self.servicer.add_dependencies(self.dependencies, self.service, 'deploy', [
            'service_2',
            'service_3:deploy',
        ], persistent_steps=True)

        self.assertEqual(self.dependencies, {
            'service_1:deploy': set(['service_2:deploy', 'service_3:deploy']),
        })

    def test_errors_if_service_does_not_exist(self):
        with self.assertRaises(ValueError) as context:
            result = self.servicer.add_dependencies(self.dependencies, self.service, 'test', 'service_0')

        self.assertTrue('Invalid service dependency specified: service_0, "service_0" must be included in services: [service_1,service_2,service_3]' in str(context.exception))

    def test_errors_if_step_does_not_exist(self):
        with self.assertRaises(ValueError) as context:
            result = self.servicer.add_dependencies(self.dependencies, self.service, 'build', 'service_2:bad_step')

        self.assertTrue('Invalid step dependency specified: service_2:bad_step, "bad_step" must be included in steps: [build,test,deploy]' in str(context.exception))

class RunServiceStepsTest(ServicerTest):
    def setUp(self):
        super().setUp()

        self.servicer.run_service_step = mock.Mock()

        self.servicer.steps = {
            'build': {'name': 'build'},
            'test': {'name': 'test'},
            'deploy': {'name': 'deploy', 'config': {'requires_service_environment': True}},
        }

        self.servicer.config = {
            'services': {
                'service_1': {
                    'name': 'service_1',
                    'steps': {
                        'build': {'config': {}},
                        'test': {'config': {}},
                        'deploy': {'config': {'type': 'deploy'}},
                    },
                },
                'service_2': {
                    'name': 'service_2',
                    'steps': {
                        'build': {'config': {}},
                        'test': {'config': {}},
                        'deploy': {'config': {'type': 'deploy'}},
                    },
                },
            },
        }

        self.servicer.service_step_order = [
            ['service_1:build', 'service_2:build'],
            ['service_1:test', 'service_2:test'],
        ]

    def test_runs_all_service_steps(self):
        result = self.servicer.run_service_steps()

        self.servicer.run_service_step.assert_has_calls([
            mock.call(self.servicer.config['services']['service_1'], {'config': {}}),
            mock.call(self.servicer.config['services']['service_2'], {'config': {}}),
            mock.call(self.servicer.config['services']['service_1'], {'config': {}}),
            mock.call(self.servicer.config['services']['service_2'], {'config': {}}),
        ])

    def test_skips_service_steps_that_require_a_service_environment(self):
        self.servicer.service_step_order = [
            ['service_1:build'],
            ['service_1:deploy'],
        ]

        result = self.servicer.run_service_steps()

        self.servicer.run_service_step.assert_has_calls([
            mock.call(self.servicer.config['services']['service_1'], {'config': {}}),
        ])

    def test_runs_service_steps_that_require_a_service_environment(self):
        self.servicer.service_environment = 'duck_tales'
        self.servicer.service_step_order = [
            ['service_1:build'],
            ['service_1:deploy'],
        ]

        result = self.servicer.run_service_steps()

        self.servicer.run_service_step.assert_has_calls([
            mock.call(self.servicer.config['services']['service_1'], {'config': {}}),
            mock.call(self.servicer.config['services']['service_1'], {'config': {'type': 'deploy'}}),
        ])

class RunServiceStepTest(ServicerTest):
    def setUp(self):
        super().setUp()

        self.servicer.run = mock.Mock()
        self.servicer.interpolate_tokens = mock.Mock()

        self.servicer.config = {}

        self.adapter = mock.Mock()
        self.adapter.up = mock.Mock(return_value='service-step results')
        self.Service = mock.Mock(return_value=self.adapter)
        self.module = self.AutoMock(Service=self.Service)

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

        self.servicer.run.assert_not_called()
        self.servicer.interpolate_tokens.assert_not_called()

    def test_runs_a_service_step_with_config_and_no_module(self):
        self.service.pop('module')

        result = self.servicer.run_service_step(self.service, self.service['steps']['build'])

        self.servicer.run.assert_not_called()
        self.servicer.interpolate_tokens.assert_not_called()

    def test_runs_a_service_step_with_module_and_no_config(self):
        self.service['steps']['build'].pop('config')

        result = self.servicer.run_service_step(self.service, self.service['steps']['build'])

        self.servicer.run.assert_not_called()
        self.servicer.interpolate_tokens.assert_not_called()

    def test_runs_a_service_step_with_module_and_config(self):
        result = self.servicer.run_service_step(self.service, self.service['steps']['build'])

        self.servicer.run.assert_not_called()
        self.servicer.interpolate_tokens.assert_called_with(self.service['steps']['build']['config'], self.servicer.config, ignore_missing_key=True)

        self.assertTrue('git' not in self.service['steps']['build']['config'])
        self.assertEqual(self.service['steps']['build']['results'], 'service-step results')

    def test_runs_a_service_step_with_git_integration(self):
        self.servicer.config['git'] = {'enabled': True}
        self.servicer.git = {}

        result = self.servicer.run_service_step(self.service, self.service['steps']['build'])

        self.servicer.run.assert_not_called()
        self.servicer.interpolate_tokens.assert_called_with(self.service['steps']['build']['config'], self.servicer.config, ignore_missing_key=True)

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

        self.servicer.run.assert_has_calls([
            mock.call('pre-command1.sh'),
            mock.call('rm -rf treeeeee xD'),
            mock.call('cowsay moo'),
            mock.call('yes | lolcat'),
        ])
