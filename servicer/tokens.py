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
        key = match[2:-1]

        if ignore_missing_key and key not in params:
            continue

        value = re.sub(r'\${%s}' % key, params[key], value)

    return value
