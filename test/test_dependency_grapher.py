from unittest import TestCase, mock

from servicer.dependency_grapher import DependencyGrapher

class DependencyGrapherTest(TestCase):
    def setUp(self):
        self.logger = mock.Mock()
        self.dependency_grapher = DependencyGrapher(
            config={
                'args': {'ignore_dependencies': False},
                'graph': {'implicit-step-dependencies': True},
                'services': {
                    'service_1': {
                        'name': 'service_1',
                        'steps': {'build': {}, 'test': {}},
                    },
                    'service_2': {
                        'name': 'service_2',
                        'steps': {'build': {}, 'test': {}, 'deploy': {}},
                    },
                },
            },
            active_services=[
                'service_1',
                'service_2',
            ],
            steps={
                'build': {'config': {}},
                'test': {'config': {}},
                'deploy': {'config': {}},
            },
            step_order=[
                'build',
                'test',
                'deploy',
            ],
            active_steps=[
                'build',
                'test',
                'deploy',
            ],
            logger=self.logger,
        )
        self.dependency_grapher.toposort2 = mock.Mock()

class DependencyGrapherTest(DependencyGrapherTest):
    def test_initialized(self):
        pass

class OrderServiceStepsTest(DependencyGrapherTest):
    def setUp(self):
        super().setUp()

        self.dependency_grapher.add_dependencies = mock.Mock()
        self.dependency_grapher.toposort2 = mock.Mock(return_value=[
            ['service_1:build', 'service_2:build'],
            ['service_1:test', 'service_2:test'],
        ])

    def test_returns_a_service_step_order(self):
        result = self.dependency_grapher.order_service_steps(self.dependency_grapher.config['services'].keys())

        self.assertEqual(self.dependency_grapher.add_dependencies.mock_calls, [
            mock.call({}, 'service_1:build', True),
            mock.call({}, 'service_1:test', True),
            mock.call({}, 'service_2:build', True),
            mock.call({}, 'service_2:test', True),
            mock.call({}, 'service_2:deploy', True),
        ])
        self.dependency_grapher.toposort2.assert_called_with({})
        self.assertEqual(result, [
            ['service_1:build', 'service_2:build'],
            ['service_1:test', 'service_2:test'],
        ])

    def test_returns_an_empty_service_step_order(self):
        self.dependency_grapher.toposort2 = mock.Mock(return_value=[])

        result = self.dependency_grapher.order_service_steps([])

        self.dependency_grapher.toposort2.assert_called_with({})
        self.assertEqual(result, [])

    def test_removes_orphaned_dependencies(self):
        def mock_add_dependencies(dependencies, service_step_name, follow_dependencies=True):
            dependencies['service_1:test'] = set(['service_1:build'])

        self.dependency_grapher.add_dependencies = mock.Mock(side_effect=mock_add_dependencies)
        self.dependency_grapher.config['args']['ignore_dependencies'] = True

        result = self.dependency_grapher.order_service_steps(self.dependency_grapher.config['services'].keys())

        self.assertEqual(self.dependency_grapher.add_dependencies.mock_calls, [
            mock.call({'service_1:test': set()}, 'service_1:build', False),
            mock.call({'service_1:test': set()}, 'service_1:test', False),
            mock.call({'service_1:test': set()}, 'service_2:build', False),
            mock.call({'service_1:test': set()}, 'service_2:test', False),
            mock.call({'service_1:test': set()}, 'service_2:deploy', False),
        ])
        self.dependency_grapher.toposort2.assert_called_with({'service_1:test': set()})
        self.assertEqual(result, [
            ['service_1:build', 'service_2:build'],
            ['service_1:test', 'service_2:test'],
        ])

class ServiceStepDependsOnTest(DependencyGrapherTest):
    def setUp(self):
        super().setUp()

        self.dependency_grapher.get_depends_on = mock.Mock(return_value=[])
        self.dependencies = {}

    def test_empty_depends_on(self):
        result = self.dependency_grapher.service_step_depends_on('service_1:build')

        self.assertEqual(self.dependency_grapher.get_depends_on.mock_calls, [
            mock.call({'name': 'service_1', 'steps': {'build': {}, 'test': {}}}),
            mock.call({}),
        ])
        self.assertEqual(result, [])

    def test_depends_on_from_service_config(self):
        self.dependency_grapher.get_depends_on.side_effect = [
            ['service_2:build', 'service_3:build'],
            [],
        ]

        result = self.dependency_grapher.service_step_depends_on('service_1:build')

        self.assertEqual(result, ['service_2:build', 'service_3:build'])

    def test_depends_on_from_service_step_config(self):
        self.dependency_grapher.get_depends_on.side_effect = [
            [],
            ['service_2:test', 'service_3:test'],
        ]

        result = self.dependency_grapher.service_step_depends_on('service_1:build')

        self.assertEqual(result, ['service_2:test', 'service_3:test'])

    def test_depends_on_from_implicit_dependencies(self):
        result = self.dependency_grapher.service_step_depends_on('service_1:test')

        self.assertEqual(result, ['service_1:build'])

    def test_depends_on_with_no_implicit_dependencies(self):
        self.dependency_grapher.config['graph']['implicit-step-dependencies'] = False

        result = self.dependency_grapher.service_step_depends_on('service_1:test')

        self.assertEqual(result, [])

    def test_depends_on_chooses_automatic_step(self):
        self.dependency_grapher.config['services']['service_3'] = {}

        self.dependency_grapher.get_depends_on.side_effect = [
            ['service_2'],
            ['service_3'],
        ]

        result = self.dependency_grapher.service_step_depends_on('service_1:build')

        self.assertEqual(result, ['service_2:build'])

class GetDependsOnTest(DependencyGrapherTest):
    def setUp(self):
        super().setUp()

    def test_returns_empty_list_if_no_depends_on(self):
        result = self.dependency_grapher.get_depends_on({})
        self.assertEqual(result, [])

    def test_returns_list_with_depends_on_as_list(self):
        result = self.dependency_grapher.get_depends_on({'depends_on': ['blackberries', 'blueberries']})
        self.assertEqual(result, ['blackberries', 'blueberries'])

    def test_returns_list_with_depends_on_as_value(self):
        result = self.dependency_grapher.get_depends_on({'depends_on': 'raspberries'})
        self.assertEqual(result, ['raspberries'])

class AddDependenciesTest(DependencyGrapherTest):
    def setUp(self):
        super().setUp()

        self.dependency_grapher.service_step_depends_on = mock.Mock(return_value=[])
        self.dependency_grapher.add_dependency = mock.Mock()

        self.dependency_grapher.config['services'] = {
            'service_1': {
                'name': 'service_1',
                'steps': {'build': {}, 'test': {}},
            },
            'service_2': {
                'name': 'service_2',
                'steps': {'build': {}, 'test': {}, 'deploy': {}},
            },
            'service_3': {
                'name': 'service_3',
                'steps': {'build': {}, 'test': {}},
            },
            'service_4': {
                'name': 'service_4',
                'steps': {'build': {}, 'deploy': {}},
            },
        }

        self.dependency_grapher.active_services = ['service_1', 'service_2']
        self.dependencies = {}

    def test_skips_if_an_entry_already_exists(self):
        self.dependencies = {'service_1:build': set(['strawberry', 'mango', 'banana'])}

        result = self.dependency_grapher.add_dependencies(self.dependencies, 'service_1:build')

        self.dependency_grapher.service_step_depends_on.assert_not_called()
        self.dependency_grapher.add_dependency.assert_not_called()
        self.assertEqual(self.dependencies, {
            'service_1:build': set(['strawberry', 'mango', 'banana']),
        })

    def test_adds_an_empty_set_with_no_dependencies(self):
        result = self.dependency_grapher.add_dependencies(self.dependencies, 'service_1:build')

        self.assertEqual(self.dependency_grapher.service_step_depends_on.mock_calls, [
            mock.call('service_1:build'),
        ])
        self.dependency_grapher.add_dependency.assert_not_called()
        self.assertEqual(self.dependencies, {
            'service_1:build': set(),
        })

    def test_adds_a_service_step_with_dependencies(self):
        self.dependency_grapher.service_step_depends_on.return_value = [
            'service_2:build',
            'service_3:build',
        ]

        result = self.dependency_grapher.add_dependencies(self.dependencies, 'service_1:build')

        self.assertEqual(self.dependency_grapher.add_dependency.mock_calls, [
            mock.call({'service_1:build': set()}, 'service_1:build', 'service_2', 'build', True),
            mock.call({'service_1:build': set()}, 'service_1:build', 'service_3', 'build', True),
        ])

    def test_adds_a_soft_service_wildcard_dependency(self):
        self.dependency_grapher.service_step_depends_on.return_value = [
            '*:build',
        ]

        result = self.dependency_grapher.add_dependencies(self.dependencies, 'service_1:build')

        self.assertEqual(self.dependency_grapher.add_dependency.mock_calls, [
            mock.call({'service_1:build': set()}, 'service_1:build', '*', 'build', False),
        ])

    def test_adds_a_hard_service_wildcard_dependency(self):
        self.dependency_grapher.service_step_depends_on.return_value = [
            '*:build!',
        ]

        result = self.dependency_grapher.add_dependencies(self.dependencies, 'service_1:build')

        self.assertEqual(self.dependency_grapher.add_dependency.mock_calls, [
            mock.call({'service_1:build': set()}, 'service_1:build', '*', 'build!', False),
        ])

    def test_throws_an_error_for_an_invalid_service_dependency(self):
        self.dependency_grapher.service_step_depends_on.return_value = [
            'service_9000:build',
        ]

        with self.assertRaises(ValueError) as context:
            result = self.dependency_grapher.add_dependencies(self.dependencies, 'service_1:build')

        self.dependency_grapher.add_dependency.assert_not_called()
        self.assertTrue('Invalid service dependency specified: service_9000:build, "service_9000" must be included in services: [service_1,service_2,service_3,service_4]' in str(context.exception))

    def test_throws_an_error_for_an_invalid_step_dependency(self):
        self.dependency_grapher.service_step_depends_on.return_value = [
            'service_2:party',
        ]

        with self.assertRaises(ValueError) as context:
            result = self.dependency_grapher.add_dependencies(self.dependencies, 'service_1:build')

        self.dependency_grapher.add_dependency.assert_not_called()
        self.assertTrue('Invalid step dependency specified: service_2:party, "party" must be included in steps: [build,test,deploy]' in str(context.exception))

class AddDependencyTest(DependencyGrapherTest):
    def setUp(self):
        super().setUp()

        self.dependency_grapher.add_dependencies = mock.Mock()

        self.dependency_grapher.active_services = ['service_1', 'service_2']
        self.dependencies = {'service_1:build': set()}

    def test_adds_a_dependency_without_following(self):
        result = self.dependency_grapher.add_dependency(self.dependencies, 'service_1:build', 'service_2', 'build', False)

        self.dependency_grapher.add_dependencies.assert_not_called()
        self.assertEqual(self.dependencies, {
            'service_1:build': set(['service_2:build']),
        })

    def test_adds_a_dependency_with_following(self):
        result = self.dependency_grapher.add_dependency(self.dependencies, 'service_1:build', 'service_2', 'build', True)

        self.dependency_grapher.add_dependencies.assert_called_with({'service_1:build': {'service_2:build'}}, 'service_2:build', True)
        self.assertEqual(self.dependencies, {
            'service_1:build': set(['service_2:build']),
        })
