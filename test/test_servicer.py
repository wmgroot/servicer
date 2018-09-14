from unittest import TestCase, mock
import os
from datetime import datetime

from servicer.servicer import Servicer

class ServicerTest(TestCase):
    def setUp(self):
        self.servicer = Servicer(args={})

    # def AutoMock(self, **attributes):
    #     automock = Mock(spec=attributes.keys())
    #     for k, v in attributes.items():
    #         setattr(automock, k, v)
    #     return automock

class ServicerClassTest(ServicerTest):
    def test_initialized(self):
        pass

class LoadEnvironmentTest(ServicerTest):
    def setUp(self):
        super().setUp()

        self.servicer.load_env_file = mock.Mock(return_value=None)

        self.args = {}

    def test_environment_variables_set(self):
        os.environ['PWD'] = 'project_path'
        result = self.servicer.load_environment(self.args)
        self.assertEqual(os.environ['PROJECT_PATH'], 'project_path')
        self.assertEqual(os.environ['BUILD_DATETIME'].split(' ')[0], datetime.now().strftime('%Y-%m-%d'))
        self.assertEqual(os.environ['BUILD_DATE'], datetime.now().strftime('%Y-%m-%d'))

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
