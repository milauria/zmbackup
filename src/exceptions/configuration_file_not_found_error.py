class ConfigurationFileNotFoundError(Exception):  # pragma: no cover
    """Configuration file not found."""

    def __init__(self, path: str):
        """
        Initialize the error.

        :param path: Path that was not found
        """
        super().__init__(f"Configuration file not found: {path}")
