class ConfigurationParseError(Exception):  # pragma: no cover
    """Error parsing configuration file."""

    def __init__(self, message: str):
        """
        Initialize the error.

        :param message: Error message
        """
        super().__init__(message)
