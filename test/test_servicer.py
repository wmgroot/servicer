from unittest import TestCase, mock

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

    def test_multiple_match(self):
        result = self.servicer.map_service_environment('env-my-branch-qa', [
            { 'branch': 'master', 'environment': 'production' },
            { 'branch': '*-qa', 'environment': 'qa' },
            { 'branch': 'env-*' },
        ])
        self.assertEqual(result, 'qa')
