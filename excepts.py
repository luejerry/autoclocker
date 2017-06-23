"""Exception classes for autoclocker."""

class ParseFailure(Exception):
    """Thrown when expected data could not be parsed from a webpage."""
    def __init__(self, msg, log):
        super().__init__(self, msg, log)

    def msg(self):
        """Get the exception message."""
        return super().args[1]

    def log(self):
        """Get the raw text that failed to parse."""
        return super().args[2]
