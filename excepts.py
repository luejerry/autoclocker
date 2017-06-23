class ParseFailure(Exception):
    def __init__(self, msg, log):
        super().__init__(self, msg, log)

    def msg(self):
        return super().args[1]

    def log(self):
        return super().args[2]
