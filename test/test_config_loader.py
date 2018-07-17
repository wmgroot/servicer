from unittest import TestCase, mock

from servicer.config_loader import ConfigLoader

class ConfigLoaderTest(TestCase):
    def setUp(self):
        self.config_loader = ConfigLoader(args={})

class ConfigLoaderClassTest(ConfigLoaderTest):
    def test_initialized(self):
        pass

class MergeConfigTest(ConfigLoaderTest):
    def setUp(self):
        super().setUp()

        self.config_loader.merge_config = mock.Mock(side_effect=self.config_loader.merge_config)

    def test_merges_empty_dicts(self):
        from_dict = {}
        to_dict = {}

        self.config_loader.merge_config(to_dict, from_dict)

        self.config_loader.merge_config.assert_has_calls([
            mock.call(to_dict, from_dict),
        ])
        self.assertEqual(to_dict, {})

    def test_merges_empty_dict_into_non_empty(self):
        from_dict = {}
        to_dict = { 'foo': 'bar' }

        self.config_loader.merge_config(to_dict, from_dict)

        self.config_loader.merge_config.assert_has_calls([
            mock.call(to_dict, from_dict),
        ])
        self.assertEqual(to_dict, { 'foo': 'bar' })

    def test_overwrites_values(self):
        from_dict = {
            'tacos': 'tacodeli',
        }
        to_dict = {
            'foo': 'bar',
            'tacos': 'torchys',
        }

        self.config_loader.merge_config(to_dict, from_dict)

        self.config_loader.merge_config.assert_has_calls([
            mock.call(to_dict, from_dict),
        ])
        self.assertEqual(to_dict, {
            'foo': 'bar',
            'tacos': 'tacodeli',
        })

    # note: list values are not combined, they are completely overwritten
    def test_overwrites_nested_values(self):
        from_dict = {
            'numbers': [4, 5, 6],
            'people': {
                'astronaut': 'buzz aldrin',
            },
            'capitols': [
                { 'brazil': 'not rio de janeiro' },
            ],
        }
        to_dict = {
            'numbers': [1, 2, 3],
            'people': {
                'astronaut': 'neil armstrong',
                'philosopher': 'socrates',
            },
            'capitols': [
                { 'france': 'paris' },
                { 'brazil': 'rio de janeiro' },
            ],
        }

        self.config_loader.merge_config(to_dict, from_dict)

        self.config_loader.merge_config.assert_has_calls([
            mock.call(to_dict, from_dict),
        ])
        self.assertEqual(to_dict, {
            'numbers': [4, 5, 6],
            'people': {
                'astronaut': 'buzz aldrin',
                'philosopher': 'socrates',
            },
            'capitols': [
                { 'brazil': 'not rio de janeiro' },
            ],
        })
