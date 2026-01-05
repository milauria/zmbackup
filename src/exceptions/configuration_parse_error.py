class ConfigurationParseError(Exception):
    """Error parsing configuration file."""
    def __init__(self, message: str):
        super().__init__(f"Error parsing configuration: {message}")
