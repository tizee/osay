"""Configuration management for osay."""

import json
from typing import Any
from pathlib import Path

CONFIG_DIR = Path.home() / '.config' / 'osay'
CONFIG_FILE = CONFIG_DIR / 'config.json'

DEFAULT_CONFIG: dict[str, Any] = {
    'audio_cache': True,
    'cleanup_enabled': True,
    'cache_expire_days': 30,
}


class Config:
    """Manages configuration from ~/.config/osay/config.json."""

    def __init__(self) -> None:
        """Load configuration from file."""
        self._config = self._load_config()

    def _load_config(self) -> dict[str, Any]:
        """Load configuration from JSON file, merged with defaults."""
        if not CONFIG_FILE.exists():
            return DEFAULT_CONFIG.copy()

        try:
            with open(CONFIG_FILE) as f:
                user_config: dict[str, Any] = json.load(f)
            config = DEFAULT_CONFIG.copy()
            config.update(user_config)
            return config
        except (json.JSONDecodeError, OSError):
            return DEFAULT_CONFIG.copy()

    @property
    def audio_cache_enabled(self) -> bool:
        """Check if audio cache is enabled."""
        result: bool = self._config.get('audio_cache', True)  # pyright: ignore[reportAssignmentType]
        return result

    @property
    def cleanup_enabled(self) -> bool:
        """Check if automatic cleanup is enabled."""
        result: bool = self._config.get('cleanup_enabled', True)  # pyright: ignore[reportAssignmentType]
        return result

    @property
    def cache_expire_days(self) -> int:
        """Get cache expiration in days."""
        result: int = self._config.get('cache_expire_days', 30)  # pyright: ignore[reportAssignmentType]
        return result
