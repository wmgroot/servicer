import re

def interpolate_tokens(config, params):
    if isinstance(config, dict):
        for key, value in config.items():
            if isinstance(value, str):
                config[key] = replace_tokens(value, params)
            else:
                interpolate_tokens(value, params)
    elif isinstance(config, list):
        for i in range(len(config)):
            if isinstance(config[i], str):
                config[i] = replace_tokens(config[i], params)
            else:
                interpolate_tokens(config[i], params)

def replace_tokens(value, params):
    for match in re.findall(r'\${.+?}', value):
        key = match[2:-1]
        value = re.sub(r'\${%s}' % key, params[key], value)

    return value
