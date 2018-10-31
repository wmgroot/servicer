from unittest import TestCase, mock

from servicer.token_interpolator import TokenInterpolator

class TokenInterpolatorTest(TestCase):
    def setUp(self):
        self.token_interpolator = TokenInterpolator()

class TokenInterpolatorClassTest(TokenInterpolatorTest):
    def test_initialized(self):
        pass

class InterpolateTokensTest(TokenInterpolatorTest):
    def setUp(self):
        super().setUp()

        self.token_interpolator.interpolate_tokens = mock.Mock(side_effect=self.token_interpolator.interpolate_tokens)
        self.token_interpolator.replace_tokens = mock.Mock()

    def test_handles_empty_dicts(self):
        config = {}
        self.token_interpolator.interpolate_tokens(config, {})

        self.assertEqual(self.token_interpolator.interpolate_tokens.mock_calls, [
            mock.call(config, {}),
        ])
        self.token_interpolator.replace_tokens.assert_not_called()

    def test_handles_empty_lists(self):
        config = []
        self.token_interpolator.interpolate_tokens(config, {})

        self.assertEqual(self.token_interpolator.interpolate_tokens.mock_calls, [
            mock.call(config, {}),
        ])
        self.token_interpolator.replace_tokens.assert_not_called()

    def test_handles_none(self):
        config = None
        self.token_interpolator.interpolate_tokens(config, {})

        self.assertEqual(self.token_interpolator.interpolate_tokens.mock_calls, [
            mock.call(config, {}),
        ])
        self.token_interpolator.replace_tokens.assert_not_called()

    def test_ignoring_non_string_values(self):
        config = {
            'foo': 123,
        }
        self.token_interpolator.interpolate_tokens(config, {})

        self.assertEqual(self.token_interpolator.interpolate_tokens.mock_calls, [
            mock.call(config, {}),
            mock.call(123, {}, False),
        ])
        self.token_interpolator.replace_tokens.assert_not_called()

    def test_replacing_string_dicts(self):
        config = {
            'foo': 'bar',
        }
        self.token_interpolator.interpolate_tokens(config, {})

        self.assertEqual(self.token_interpolator.interpolate_tokens.mock_calls, [
            mock.call(config, {}),
        ])
        self.assertEqual(self.token_interpolator.replace_tokens.mock_calls, [
            mock.call('bar', {}, False),
        ])

    def test_replacing_string_lists(self):
        config = ['foo', 'bar']
        self.token_interpolator.interpolate_tokens(config, {})

        self.assertEqual(self.token_interpolator.interpolate_tokens.mock_calls, [
            mock.call(config, {}),
        ])
        self.assertEqual(self.token_interpolator.replace_tokens.mock_calls, [
            mock.call('foo', {}, False),
            mock.call('bar', {}, False),
        ])

    def test_replacing_complex_nested_strings(self):
        config = {
            'colors': ['red', 'blue'],
            'fish': {
                'tilapia': 'ok',
                'salmon': 'nice',
                'tuna': {
                    'flavors': ['fishy', 'fresh', 'salty'],
                    'feelings': 'various',
                },
            },
        }
        self.token_interpolator.interpolate_tokens(config, {})

        self.assertEqual(self.token_interpolator.interpolate_tokens.mock_calls, [
            mock.call(config, {}),
            mock.call(config['colors'], {}, False),
            mock.call(config['fish'], {}, False),
            mock.call(config['fish']['tuna'], {}, False),
            mock.call(config['fish']['tuna']['flavors'], {}, False),
        ])
        self.assertEqual(self.token_interpolator.replace_tokens.mock_calls, [
            mock.call('red', {}, False),
            mock.call('blue', {}, False),
            mock.call('ok', {}, False),
            mock.call('nice', {}, False),
            mock.call('fishy', {}, False),
            mock.call('fresh', {}, False),
            mock.call('salty', {}, False),
            mock.call('various', {}, False),
        ])

    def test_passing_params(self):
        config = {
            'colors': ['red', 'blue'],
        }
        self.token_interpolator.interpolate_tokens(config, {'foo': 'bar'})

        self.assertEqual(self.token_interpolator.interpolate_tokens.mock_calls, [
            mock.call(config, {'foo': 'bar'}),
            mock.call(config['colors'], {'foo': 'bar'}, False),
        ])
        self.assertEqual(self.token_interpolator.replace_tokens.mock_calls, [
            mock.call('red', {'foo': 'bar'}, False),
            mock.call('blue', {'foo': 'bar'}, False),
        ])

    def test_passing_ignore_missing_key(self):
        config = {
            'colors': ['red', 'blue'],
        }
        self.token_interpolator.interpolate_tokens(config, {}, ignore_missing_key=True)

        self.assertEqual(self.token_interpolator.interpolate_tokens.mock_calls, [
            mock.call(config, {}, ignore_missing_key=True),
            mock.call(config['colors'], {}, True),
        ])
        self.assertEqual(self.token_interpolator.replace_tokens.mock_calls, [
            mock.call('red', {}, True),
            mock.call('blue', {}, True),
        ])

class ReplaceTokensTest(TokenInterpolatorTest):
    def setUp(self):
        super().setUp()

        self.token_interpolator.evaluate_token = mock.Mock(return_value=None)

    def test_handles_empty_string(self):
        result = self.token_interpolator.replace_tokens('', {})

        self.token_interpolator.evaluate_token.assert_not_called()
        self.assertEqual(result, '')

    def test_does_not_replace_a_string(self):
        result = self.token_interpolator.replace_tokens('foo', {})

        self.token_interpolator.evaluate_token.assert_not_called()
        self.assertEqual(result, 'foo')

    def test_replaces_a_string(self):
        self.token_interpolator.evaluate_token.return_value = 'red'

        result = self.token_interpolator.replace_tokens('${ONE}', {})

        self.assertEqual(self.token_interpolator.evaluate_token.mock_calls, [
            mock.call('${ONE}', {}),
        ])
        self.assertEqual(result, 'red')

    def test_replaces_multiple_strings(self):
        self.token_interpolator.evaluate_token.side_effect = [
            'red',
            'blue',
        ]

        result = self.token_interpolator.replace_tokens('${ONE}+${TWO}', {})

        self.assertEqual(self.token_interpolator.evaluate_token.mock_calls, [
            mock.call('${ONE}', {}),
            mock.call('${TWO}', {}),
        ])
        self.assertEqual(result, 'red+blue')

    def test_replaces_nested_strings(self):
        self.token_interpolator.evaluate_token.side_effect = [
            'red',
        ]

        result = self.token_interpolator.replace_tokens('${ONE:${TWO}}', {})

        self.assertEqual(self.token_interpolator.evaluate_token.mock_calls, [
            mock.call('${ONE:${TWO}}', {}),
        ])
        self.assertEqual(result, 'red')

class EvaluateTokenTest(TokenInterpolatorTest):
    def setUp(self):
        super().setUp()

        # once I think hard enough about how to recurse this
        # self.token_interpolator.evaluate_token = mock.Mock(side_effect=self.token_interpolator.evaluate_token)
        self.token_interpolator.evaluate_value = mock.Mock(return_value=None)

    def test_handles_default_values_with_no_evaluated_value(self):
        result = self.token_interpolator.evaluate_token('${TWO:family.genus.species}', {})

        self.assertEqual(self.token_interpolator.evaluate_value.mock_calls, [
            mock.call('TWO', {}),
            mock.call('family.genus.species', {}),
        ])
        self.assertEqual(result, None)

    def test_handles_default_values_with_an_evaluated_value(self):
        self.token_interpolator.evaluate_value = mock.Mock(side_effect=[
            None,
            'bear',
        ])

        result = self.token_interpolator.evaluate_token('${TWO:family.genus.species}', {})

        self.assertEqual(self.token_interpolator.evaluate_value.mock_calls, [
            mock.call('TWO', {}),
            mock.call('family.genus.species', {}),
        ])
        self.assertEqual(result, 'bear')

    def test_ignores_default_value_with_an_evaluated_value(self):
        self.token_interpolator.evaluate_value = mock.Mock(side_effect=[
            'blue',
        ])

        result = self.token_interpolator.evaluate_token('${TWO:family.genus.species}', {})

        self.assertEqual(self.token_interpolator.evaluate_value.mock_calls, [
            mock.call('TWO', {}),
        ])
        self.assertEqual(result, 'blue')

    def test_finds_single_evaluated_value(self):
        self.token_interpolator.evaluate_value = mock.Mock(side_effect=[
            'blue',
        ])

        result = self.token_interpolator.evaluate_token('${TWO}', {})

        self.assertEqual(self.token_interpolator.evaluate_value.mock_calls, [
            mock.call('TWO', {}),
        ])
        self.assertEqual(result, 'blue')

class EvaluateValueTest(TokenInterpolatorTest):
    def setUp(self):
        super().setUp()

        self.token_interpolator.dict_get_path = mock.Mock(return_value=None)

    def test_evaluates_a_single_string(self):
        result = self.token_interpolator.evaluate_value('tacos', {})

        self.token_interpolator.dict_get_path.assert_called_with(
            path=['tacos'],
            _dict={},
            ignore_missing_key=True,
        )
        self.assertEqual(result, None)

    def test_evaluates_a_string_path(self):
        params = {
            'crunchy': {
                'supreme': {
                    'doritos': 'locos',
                },
            },
        }
        self.token_interpolator.dict_get_path.return_value = 'locos'
        result = self.token_interpolator.evaluate_value('crunchy.supreme.doritos', params)

        self.token_interpolator.dict_get_path.assert_called_with(
            path=['crunchy', 'supreme', 'doritos'],
            _dict=params,
            ignore_missing_key=True,
        )
        self.assertEqual(result, 'locos')

    def test_evaluates_string_but_not_found(self):
        result = self.token_interpolator.evaluate_value('crunchy.supreme.doritos', {})

        self.token_interpolator.dict_get_path.assert_called_with(
            path=['crunchy', 'supreme', 'doritos'],
            _dict={},
            ignore_missing_key=True,
        )
        self.assertEqual(result, None)

class DictGetPathTest(TokenInterpolatorTest):
    def setUp(self):
        super().setUp()

        self.token_interpolator.dict_get_path = mock.Mock(side_effect=self.token_interpolator.dict_get_path)

    def test_none_path(self):
        result = self.token_interpolator.dict_get_path(path=None, _dict={})

        self.assertEqual(self.token_interpolator.dict_get_path.mock_calls, [
            mock.call(path=None, _dict={}),
        ])
        self.assertEqual(result, None)

    def test_empty_path(self):
        result = self.token_interpolator.dict_get_path(path=[], _dict={})

        self.assertEqual(self.token_interpolator.dict_get_path.mock_calls, [
            mock.call(path=[], _dict={}),
        ])
        self.assertEqual(result, None)

    def test_simple_path(self):
        path = ['egg']
        _dict = {'egg': 'whites'}
        result = self.token_interpolator.dict_get_path(path=path, _dict=_dict)

        self.assertEqual(self.token_interpolator.dict_get_path.mock_calls, [
            mock.call(path=path, _dict=_dict),
        ])
        self.assertEqual(result, 'whites')

    def test_a_magnificent_path(self):
        path = ['terrifying', 'beautiful', 'powerful']
        _dict = {
            'terrifying': {
                'beautiful': {
                    'powerful': 'grey prince zote',
                },
            },
        }
        result = self.token_interpolator.dict_get_path(path=path, _dict=_dict)

        self.assertEqual(self.token_interpolator.dict_get_path.mock_calls, [
            mock.call(path=['terrifying', 'beautiful', 'powerful'], _dict=_dict),
            mock.call(path=['beautiful', 'powerful'], _dict=_dict['terrifying'], ignore_missing_key=False),
            mock.call(path=['powerful'], _dict=_dict['terrifying']['beautiful'], ignore_missing_key=False),
        ])
        self.assertEqual(result, 'grey prince zote')

    def test_throws_key_error_for_invalid_path(self):
        path = ['terrifying', 'awful', 'powerful']
        _dict = {
            'terrifying': {
                'beautiful': {
                    'powerful': 'grey prince zote',
                },
            },
        }
        with self.assertRaises(KeyError) as context:
            result = self.token_interpolator.dict_get_path(path=path, _dict=_dict)

        self.assertTrue('awful' in str(context.exception))

    def test_allows_missing_path(self):
        path = ['terrifying', 'awful', 'powerful']
        _dict = {
            'terrifying': {
                'beautiful': {
                    'powerful': 'grey prince zote',
                },
            },
        }
        result = self.token_interpolator.dict_get_path(path=path, _dict=_dict, ignore_missing_key=True)

        self.assertEqual(self.token_interpolator.dict_get_path.mock_calls, [
            mock.call(path=['terrifying', 'awful', 'powerful'], _dict=_dict, ignore_missing_key=True),
            mock.call(path=['awful', 'powerful'], _dict=_dict['terrifying'], ignore_missing_key=True),
        ])
        self.assertEqual(result, None)
