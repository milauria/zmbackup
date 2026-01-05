class ConfigurationValidationError(Exception):  # pragma: no cover
    """Configuration validation failed."""

    def __init__(self, message: str):
        """
        Initialize the error.

        :param message: Error message
        """
        super().__init__(message)
