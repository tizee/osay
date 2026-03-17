"""Tests for osay.key module."""

import os
import json
import stat
from pathlib import Path
from unittest.mock import patch

from osay.key import load_api_key, save_api_key, ensure_api_key, remove_api_key


class TestLoadApiKey:
    def test_prefers_env_var(self, tmp_path: Path):
        fake_key_file = tmp_path / 'key.json'
        fake_key_file.write_text(json.dumps({'OPENAI_API_KEY': 'sk-from-file'}))
        with (
            patch('osay.key.KEY_FILE', fake_key_file),
            patch.dict(os.environ, {'OPENAI_API_KEY': 'sk-from-env'}),
        ):
            assert load_api_key() == 'sk-from-env'

    def test_loads_from_file(self, tmp_path: Path):
        fake_key_file = tmp_path / 'key.json'
        fake_key_file.write_text(json.dumps({'OPENAI_API_KEY': 'sk-from-file'}))
        with (
            patch('osay.key.KEY_FILE', fake_key_file),
            patch.dict(os.environ, {}, clear=True),
        ):
            # Remove OPENAI_API_KEY if present
            os.environ.pop('OPENAI_API_KEY', None)
            assert load_api_key() == 'sk-from-file'

    def test_returns_none_when_missing(self, tmp_path: Path):
        fake_key_file = tmp_path / 'key.json'
        with (
            patch('osay.key.KEY_FILE', fake_key_file),
            patch.dict(os.environ, {}, clear=True),
        ):
            os.environ.pop('OPENAI_API_KEY', None)
            assert load_api_key() is None

    def test_returns_none_on_corrupt_file(self, tmp_path: Path):
        fake_key_file = tmp_path / 'key.json'
        fake_key_file.write_text('not json')
        with (
            patch('osay.key.KEY_FILE', fake_key_file),
            patch.dict(os.environ, {}, clear=True),
        ):
            os.environ.pop('OPENAI_API_KEY', None)
            assert load_api_key() is None


class TestSaveApiKey:
    def test_saves_and_sets_permissions(self, tmp_path: Path):
        fake_dir = tmp_path / 'osay'
        fake_key_file = fake_dir / 'key.json'
        with (
            patch('osay.key.CONFIG_DIR', fake_dir),
            patch('osay.key.KEY_FILE', fake_key_file),
        ):
            result = save_api_key('sk-test-key-12345')

        assert result == fake_key_file
        assert fake_key_file.exists()

        data = json.loads(fake_key_file.read_text())
        assert data['OPENAI_API_KEY'] == 'sk-test-key-12345'

        # Check 0600 permissions
        mode = fake_key_file.stat().st_mode
        assert mode & 0o777 == stat.S_IRUSR | stat.S_IWUSR


class TestRemoveApiKey:
    def test_removes_existing(self, tmp_path: Path):
        fake_key_file = tmp_path / 'key.json'
        fake_key_file.write_text('{}')
        with patch('osay.key.KEY_FILE', fake_key_file):
            assert remove_api_key() is True
        assert not fake_key_file.exists()

    def test_returns_false_when_missing(self, tmp_path: Path):
        fake_key_file = tmp_path / 'key.json'
        with patch('osay.key.KEY_FILE', fake_key_file):
            assert remove_api_key() is False


class TestEnsureApiKey:
    def test_exports_to_env(self, tmp_path: Path):
        fake_key_file = tmp_path / 'key.json'
        fake_key_file.write_text(json.dumps({'OPENAI_API_KEY': 'sk-exported'}))
        with (
            patch('osay.key.KEY_FILE', fake_key_file),
            patch.dict(os.environ, {}, clear=True),
        ):
            os.environ.pop('OPENAI_API_KEY', None)
            result = ensure_api_key()
            assert result == 'sk-exported'
            assert os.environ['OPENAI_API_KEY'] == 'sk-exported'

    def test_returns_none_when_no_key(self, tmp_path: Path):
        fake_key_file = tmp_path / 'key.json'
        with (
            patch('osay.key.KEY_FILE', fake_key_file),
            patch.dict(os.environ, {}, clear=True),
        ):
            os.environ.pop('OPENAI_API_KEY', None)
            assert ensure_api_key() is None
