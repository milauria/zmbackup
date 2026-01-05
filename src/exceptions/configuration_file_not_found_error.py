from .configuration_error import ConfigurationError

class ConfigurationFileNotFoundError(ConfigurationError):
    """Configuration file not found."""
    pass
