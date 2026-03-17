"""Tests for osay.config module."""

import json
from pathlib import Path
from unittest.mock import patch

from osay.config import DEFAULT_CONFIG, Config


class TestConfig:
    def test_defaults_when_no_file(self, tmp_path: Path):
        fake_config = tmp_path / 'config.json'
        with patch('osay.config.CONFIG_FILE', fake_config):
            config = Config()
        assert config.audio_cache_enabled is True
        assert config.cleanup_enabled is True
        assert config.cache_expire_days == 30

    def test_loads_user_config(self, tmp_path: Path):
        fake_config = tmp_path / 'config.json'
        fake_config.write_text(json.dumps({'audio_cache': False, 'cache_expire_days': 7}))
        with patch('osay.config.CONFIG_FILE', fake_config):
            config = Config()
        assert config.audio_cache_enabled is False
        assert config.cache_expire_days == 7
        # cleanup_enabled falls back to default
        assert config.cleanup_enabled is True

    def test_invalid_json_falls_back_to_defaults(self, tmp_path: Path):
        fake_config = tmp_path / 'config.json'
        fake_config.write_text('not valid json{{{')
        with patch('osay.config.CONFIG_FILE', fake_config):
            config = Config()
        assert config.audio_cache_enabled is DEFAULT_CONFIG['audio_cache']
        assert config.cache_expire_days == DEFAULT_CONFIG['cache_expire_days']
