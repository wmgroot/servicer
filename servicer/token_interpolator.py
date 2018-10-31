import re

class TokenInterpolator():
    def interpolate_tokens(self, config, params, ignore_missing_key=False):
        if isinstance(config, dict):
            for key, value in config.items():
                if isinstance(value, str):
                    config[key] = self.replace_tokens(value, params, ignore_missing_key)
                else:
                    self.interpolate_tokens(value, params, ignore_missing_key)
        elif isinstance(config, list):
            for i in range(len(config)):
                if isinstance(config[i], str):
                    config[i] = self.replace_tokens(config[i], params, ignore_missing_key)
                else:
                    self.interpolate_tokens(config[i], params, ignore_missing_key)

    def replace_tokens(self, value, params, ignore_missing_key=False):
        escaped_values = list('.^$*+?()[]{}|')

        for match in re.findall(r'\${.+?}+', value):
            token = match[2:-1]

            replace_value = self.evaluate_token(match, params)

            if replace_value:
                for ev in escaped_values:
                    if ev in token:
                        token = token.replace(ev, '\%s' % ev)
                value = re.sub(r'\${%s}' % token, replace_value, value)

        return value

    def evaluate_token(self, value, params):
        if not (value.startswith('${') and value.endswith('}')):
            return value

        pieces = value[2:-1].split(':')
        if len(pieces) > 2:
            pieces[1] = ':'.join(pieces[1:])
            pieces = pieces[:2]

        for p in pieces:
            evaluated = self.evaluate_value(p, params)
            if evaluated:
                return evaluated

        return None

    def evaluate_value(self, value, params):
        if value.startswith('"') and value.endswith('"'):
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
