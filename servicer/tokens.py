import re

def interpolate_tokens(config, params, ignore_missing_key=False):
    if isinstance(config, dict):
        for key, value in config.items():
            if isinstance(value, str):
                config[key] = replace_tokens(value, params, ignore_missing_key)
            else:
                interpolate_tokens(value, params, ignore_missing_key)
    elif isinstance(config, list):
        for i in range(len(config)):
            if isinstance(config[i], str):
                config[i] = replace_tokens(config[i], params, ignore_missing_key)
            else:
                interpolate_tokens(config[i], params, ignore_missing_key)

def replace_tokens(value, params, ignore_missing_key=False):
    for match in re.findall(r'\${.+?}', value):
        token = match[2:-1]
        pieces = token.split(':')
        key = pieces[0]

        replace_value = None
        if key not in params:
            if ignore_missing_key:
                continue
            elif len(pieces) > 1:
                # use default value
                replace_value = pieces[1]


        if replace_value == None:
            replace_value = params[key]

        value = re.sub(r'\${%s}' % token, replace_value, value)

    return value
