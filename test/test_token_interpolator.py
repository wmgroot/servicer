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

        def evaluate_value(value, params):
            return value

        self.token_interpolator.replace_tokens = mock.Mock(side_effect=self.token_interpolator.replace_tokens)
        self.token_interpolator.evaluate_value = mock.Mock(side_effect=evaluate_value)

    def test_handles_empty_string(self):
        result = self.token_interpolator.replace_tokens('', {})

        self.assertEqual(self.token_interpolator.replace_tokens.mock_calls, [
            mock.call('', {}),
        ])
        self.token_interpolator.evaluate_value.assert_not_called()
        self.assertEqual(result, '')

    def test_does_not_replace_a_string(self):
        result = self.token_interpolator.replace_tokens('foo', {})

        self.assertEqual(self.token_interpolator.replace_tokens.mock_calls, [
            mock.call('foo', {}),
        ])
        self.token_interpolator.evaluate_value.assert_not_called()
        self.assertEqual(result, 'foo')

    def test_replaces_a_string(self):
        params = {'ONE': 'red'}
        result = self.token_interpolator.replace_tokens('${ONE}', params)

        self.assertEqual(self.token_interpolator.replace_tokens.mock_calls, [
            mock.call('${ONE}', params),
        ])
        self.assertEqual(self.token_interpolator.evaluate_value.mock_calls, [
            mock.call('red', params),
        ])
        self.assertEqual(result, 'red')

    def test_replaces_multiple_strings(self):
        params = {'ONE': 'red', 'TWO': 'blue'}
        result = self.token_interpolator.replace_tokens('${TWO}+${ONE}', params)

        self.assertEqual(self.token_interpolator.replace_tokens.mock_calls, [
            mock.call('${TWO}+${ONE}', params),
        ])
        self.assertEqual(self.token_interpolator.evaluate_value.mock_calls, [
            mock.call('blue', params),
            mock.call('red', params),
        ])
        self.assertEqual(result, 'blue+red')

    def test_ignores_default_value_if_matched(self):
        params = {'ONE': 'red', 'TWO': 'blue', 'THREE': 'green'}
        result = self.token_interpolator.replace_tokens('${TWO:2} bears', params)

        self.assertEqual(self.token_interpolator.replace_tokens.mock_calls, [
            mock.call('${TWO:2} bears', params),
        ])
        self.assertEqual(self.token_interpolator.evaluate_value.mock_calls, [
            mock.call('blue', params),
        ])
        self.assertEqual(result, 'blue bears')

    def test_falls_back_to_default_value(self):
        params = {'ONE': 'red', 'THREE': 'green'}
        result = self.token_interpolator.replace_tokens('${TWO:2} bears', params)

        self.assertEqual(self.token_interpolator.replace_tokens.mock_calls, [
            mock.call('${TWO:2} bears', params),
            mock.call('2', params, ignore_missing_key=False),
        ])
        self.assertEqual(self.token_interpolator.evaluate_value.mock_calls, [
            mock.call('2', params),
        ])
        self.assertEqual(result, '2 bears')

    def test_evaluating_a_default_value(self):
        params = {'ONE': 'red', 'family': {'genus': {'species': 'fuzzy'}}}
        result = self.token_interpolator.replace_tokens('${TWO:{family.genus.species}} bears', params)

        self.assertEqual(self.token_interpolator.replace_tokens.mock_calls, [
            mock.call('${TWO:{family.genus.species}} bears', params),
            mock.call('{family.genus.species}', params, ignore_missing_key=False),
        ])
        self.assertEqual(self.token_interpolator.evaluate_value.mock_calls, [
            mock.call('{family.genus.species}', params),
        ])
        self.assertEqual(result, '{family.genus.species} bears')

    def test_defaults_multiples_times(self):
        params = {'ONE': 'red', 'THREE': 'green'}
        result = self.token_interpolator.replace_tokens('${TWO:${THREE}} bears', params)

        self.assertEqual(self.token_interpolator.replace_tokens.mock_calls, [
            mock.call('${TWO:${THREE}} bears', params),
            mock.call('${THREE}', params, ignore_missing_key=False),
        ])
        self.assertEqual(self.token_interpolator.evaluate_value.mock_calls, [
            mock.call('green', params),
            mock.call('green', params),
        ])
        self.assertEqual(result, 'green bears')

    def test_nested_defaults(self):
        params = {'ONE': 'red', 'THREE': 'green'}
        result = self.token_interpolator.replace_tokens('${TWO:${FOUR:black}} bears', params)

        self.assertEqual(self.token_interpolator.replace_tokens.mock_calls, [
            mock.call('${TWO:${FOUR:black}} bears', params),
            mock.call('${FOUR:black}', params, ignore_missing_key=False),
            mock.call('black', params, ignore_missing_key=False),
        ])
        self.assertEqual(self.token_interpolator.evaluate_value.mock_calls, [
            mock.call('black', params),
            mock.call('black', params),
        ])
        self.assertEqual(result, 'black bears')

    def test_ignores_missing_key(self):
        params = {'ONE': 'red', 'THREE': 'green'}
        result = self.token_interpolator.replace_tokens('${TWO} bears', params, ignore_missing_key=True)

        self.assertEqual(self.token_interpolator.replace_tokens.mock_calls, [
            mock.call('${TWO} bears', params, ignore_missing_key=True),
        ])
        self.assertEqual(self.token_interpolator.evaluate_value.mock_calls, [
            mock.call('${TWO}', params),
        ])
        self.assertEqual(result, '${TWO} bears')

    def test_ignores_missing_key_but_prefers_default(self):
        params = {'ONE': 'red', 'THREE': 'green'}
        result = self.token_interpolator.replace_tokens('${TWO:polar} bears', params, ignore_missing_key=True)

        self.assertEqual(self.token_interpolator.replace_tokens.mock_calls, [
            mock.call('${TWO:polar} bears', params, ignore_missing_key=True),
            mock.call('polar', params, ignore_missing_key=True),
        ])
        self.assertEqual(self.token_interpolator.evaluate_value.mock_calls, [
            mock.call('polar', params),
        ])
        self.assertEqual(result, 'polar bears')

class EvaluateValueTest(TokenInterpolatorTest):
    def setUp(self):
        super().setUp()

        self.token_interpolator.dict_get_path = mock.Mock()

    def test_handles_empty_string(self):
        result = self.token_interpolator.evaluate_value('', {})

        self.token_interpolator.dict_get_path.assert_not_called()
        self.assertEqual(result, '')

    def test_ignores_non_eval_string(self):
        result = self.token_interpolator.evaluate_value('tacos', {})

        self.token_interpolator.dict_get_path.assert_not_called()
        self.assertEqual(result, 'tacos')

    def test_evaluates_a_string(self):
        params = {
            'crunchy': {
                'supreme': {
                    'doritos': 'locos',
                },
            },
        }
        self.token_interpolator.dict_get_path.return_value = 'locos'
        result = self.token_interpolator.evaluate_value('{crunchy.supreme.doritos}', params)

        self.token_interpolator.dict_get_path.assert_called_with(
            path=['crunchy', 'supreme', 'doritos'],
            _dict=params,
            ignore_missing_key=True,
        )
        self.assertEqual(result, 'locos')

    def test_evaluates_string_but_not_found(self):
        self.token_interpolator.dict_get_path.return_value = None
        result = self.token_interpolator.evaluate_value('{crunchy.supreme.doritos}', {})

        self.token_interpolator.dict_get_path.assert_called_with(
            path=['crunchy', 'supreme', 'doritos'],
            _dict={},
            ignore_missing_key=True,
        )
        self.assertEqual(result, '{crunchy.supreme.doritos}')

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
