class APIError(Exception):
    """An error whose message is safe to return to API clients."""

    def __init__(self, status, code, message):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
