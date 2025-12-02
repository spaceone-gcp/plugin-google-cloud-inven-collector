"""Google Cloud client common configuration management module

This module centrally manages retry and timeout settings for Google Cloud clients.
Configuration priority: options parameter > default constants
"""

import logging
from typing import Optional

_LOGGER = logging.getLogger("spaceone")

# Default constants
DEFAULT_MAX_RETRY_ATTEMPTS = 1
DEFAULT_TIMEOUT_SECONDS = 120


class ClientConfig:
    """Class for managing Google Cloud client configuration"""

    def __init__(self, options: dict = None):
        """Initialize configuration.

        Args:
            options: Options dictionary passed from collector_collect function
        """
        options = options or {}

        # Load configuration values (options -> default values order)
        self.max_retry_attempts = int(
            options.get("max_retry_attempts") or DEFAULT_MAX_RETRY_ATTEMPTS
        )

        self.timeout_seconds = float(
            options.get("timeout_seconds") or DEFAULT_TIMEOUT_SECONDS
        )

        _LOGGER.debug(
            f"Google Cloud client configuration: "
            f"max_retry_attempts={self.max_retry_attempts}, "
            f"timeout={self.timeout_seconds}s"
        )

    def get_max_retry_attempts(self) -> int:
        """Return max retry attempts."""
        return self.max_retry_attempts

    def get_timeout(self) -> int:
        """Return HTTP timeout configuration."""
        return self.timeout_seconds


class ClientConfigManager:
    """Manager for globally managing Google Cloud client configuration"""

    _config: Optional[ClientConfig] = None

    @classmethod
    def initialize(cls, options: dict = None) -> None:
        """Initialize global configuration.

        Args:
            options: Configuration options dictionary
        """
        cls._config = ClientConfig(options)
        _LOGGER.info("Google Cloud client configuration initialization completed")

    @classmethod
    def get_config(cls) -> ClientConfig:
        """Return current configuration.

        Returns:
            ClientConfig instance

        Note:
            Auto-initializes with defaults if not initialized
        """
        if cls._config is None:
            cls.initialize()
            _LOGGER.debug("ClientConfigManager auto-initialized with default values")
        return cls._config

    @classmethod
    def is_initialized(cls) -> bool:
        """Check if configuration is initialized.

        Returns:
            True if initialized, False otherwise
        """
        return cls._config is not None
