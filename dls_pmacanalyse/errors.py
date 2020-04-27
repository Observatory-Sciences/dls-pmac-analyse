class PmacReadError(Exception):
    """PMAC read error exception."""

    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message


class ArgumentError(Exception):
    """Command line argument error exception."""

    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message


class ConfigError(Exception):
    """Configuration file error exception."""

    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message


class AnalyseError(Exception):
    """Analysis error exception."""

    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message


class LexerError(Exception):
    """Lexer error exception."""

    def __init__(self, token, fileName, line):
        self.token = token
        self.fileName = fileName
        self.line = line

    def __str__(self):
        return "[%s:%s] Unknown token: %s" % (self.fileName, self.line, self.token)


class ParserError(Exception):
    """Parser error exception."""

    def __init__(self, message, token):
        self.message = message
        self.line = token.line
        self.fileName = token.fileName

    def __str__(self):
        return "[%s:%s] %s" % (self.fileName, self.line, self.message)


class GeneralError(Exception):
    """General error exception."""

    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message
