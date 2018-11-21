class Logger():
    def __init__(self, level='info'):
        self.level = level

        self.levels = [
            'debug',
            'info',
            'warn',
            'error',
        ]

    def log(self, message='', level='info'):
        if self.levels.index(level) >= self.levels.index(self.level):
            print(message)
