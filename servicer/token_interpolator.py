import re

class TokenInterpolator():
    def __init__(self, logger=None):
        self.logger = logger

    def interpolate_tokens(self, config, params, ignore_missing_key=False, ignore_default=False):
        if isinstance(config, dict):

            keys_to_change = []
            for key in config.keys():
                new_key = self.replace_tokens(key, params, ignore_missing_key, ignore_default)
                if new_key is not None and new_key not in config.keys():
                    keys_to_change.append((key, new_key))

            for k in keys_to_change:
                config[k[1]] = config[k[0]]
                config.pop(k[0])

            for key, value in config.items():
                if isinstance(value, str):
                    config[key] = self.replace_tokens(value, params, ignore_missing_key, ignore_default)
                else:
                    self.interpolate_tokens(value, params, ignore_missing_key, ignore_default)

        elif isinstance(config, list):

            for i in range(len(config)):
                if isinstance(config[i], str):
                    config[i] = self.replace_tokens(config[i], params, ignore_missing_key, ignore_default)
                else:
                    self.interpolate_tokens(config[i], params, ignore_missing_key, ignore_default)

    def replace_tokens(self, value, params, ignore_missing_key=False, ignore_default=False):
        escaped_values = list('.^$*+?()[]{}|')

        for match in re.findall(r'\${.+?}+', value):
            token = match[2:-1]

            replace_value = self.evaluate_token(match, params, ignore_default)

            # allow list replacement, replace entire string value with the list
            if isinstance(replace_value, list):
                return replace_value

            if replace_value:
                for ev in escaped_values:
                    if ev in token:
                        token = token.replace(ev, '\%s' % ev)
                # self.logger.log('replacing token %s -> %s' % (token, replace_value), level='debug')
                value = re.sub(r'\${%s}' % token, replace_value, value)

        return value

    def evaluate_token(self, value, params, ignore_default=False):
        if not (value.startswith('${') and value.endswith('}')):
            return value

        pieces = value[2:-1].split(':')
        if len(pieces) > 2:
            pieces[1] = ':'.join(pieces[1:])
            pieces = pieces[:2]

        if ignore_default:
            pieces = pieces[0:1]

        for p in pieces:
            evaluated = self.evaluate_value(p, params)
            if evaluated:
                return evaluated

        return None

    def evaluate_value(self, value, params):
        if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
            return value[1:-1]

        result = None
        path_pieces = value.split('.')
        if len(path_pieces) > 0:
            path_value = self.dict_get_path(_dict=params, path=path_pieces, ignore_missing_key=True)
            if path_value:
                result = path_value

        return result

    def dict_get_path(self, _dict={}, path=[], ignore_missing_key=False):
        if path == None or len(path) < 1:
            return None

        _path = path.copy()
        current_path = _path.pop(0)
        if ignore_missing_key and current_path not in _dict:
            return None

        if len(_path) < 1:
            return _dict[current_path]

        return self.dict_get_path(_dict=_dict[current_path], path=_path, ignore_missing_key=ignore_missing_key)
