class Logger():
    def __init__(self, level='info'):
        self.level = level

        self.levels = [
            'debug',
            'info',
            'warn',
            'error',
        ]
        self.level_config = {
            'debug': {
                'prefix': 'DEBUG: ',
            },
            'info': {},
            'warn': {
                'prefix': 'WARNING: ',
            },
            'error': {
                'prefix': 'ERROR: ',
            },
        }

    def log(self, message='', level='info'):
        if self.levels.index(level) >= self.levels.index(self.level):
            if 'prefix' in self.level_config[level] and self.level_config[level]['prefix']:
                message = self.level_config[level]['prefix'] + message

            print(message)
