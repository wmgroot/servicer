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
            replace_value = None

            pieces = token.split(':')
            if len(pieces) > 2:
                pieces[1] = ':'.join(pieces[1:])
                pieces = pieces[:2]

            key = pieces[0]

            if key not in params:
                if len(pieces) > 1:
                    # use default value
                    replace_value = self.replace_tokens(pieces[1], params, ignore_missing_key=ignore_missing_key)
                elif ignore_missing_key:
                    replace_value = '${%s}' % ':'.join(pieces)

            if replace_value == None:
                replace_value = params[key]

            if replace_value != None:
                for ev in escaped_values:
                    if ev in token:
                        token = token.replace(ev, '\%s' % ev)

                replace_value = self.evaluate_value(replace_value, params)

                value = re.sub(r'\${%s}' % token, replace_value, value)

        return value

    def evaluate_value(self, value, params):
        if not (value.startswith('{') and value.endswith('}')):
            return value

        path_pieces = value[1:-1].split('.')
        if len(path_pieces) > 0:
            path_value = self.dict_get_path(_dict=params, path=path_pieces, ignore_missing_key=True)
            if path_value:
                value = path_value

        return value

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
