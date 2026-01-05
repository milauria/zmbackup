class ConfigurationValidationError(Exception):
    """Configuration validation failed."""

    def __init__(self, message: str):
        super().__init__(f"Configuration validation failed: {message}")
