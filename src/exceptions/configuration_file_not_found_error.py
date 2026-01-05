class ConfigurationFileNotFoundError(Exception):
    """Configuration file not found."""
    def __init__(self, path: str):
        self.path = path
        super().__init__(f"Configuration file not found: {path}")
