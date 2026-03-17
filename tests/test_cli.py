"""Tests for osay.cli module."""

import os
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from osay.cli import EXIT_NO_INPUT, main, _build_parser


class TestBuildParser:
    def test_parser_has_expected_arguments(self):
        parser = _build_parser()
        # Smoke test: parse known args
        args = parser.parse_args(['hello world'])
        assert args.text == 'hello world'
        assert args.json_output is False

    def test_parser_json_flag(self):
        parser = _build_parser()
        args = parser.parse_args(['--json', 'hello'])
        assert args.json_output is True

    def test_parser_setup_direct_key(self):
        parser = _build_parser()
        args = parser.parse_args(['--setup', 'sk-test123'])
        assert args.setup == 'sk-test123'

    def test_parser_setup_interactive(self):
        parser = _build_parser()
        args = parser.parse_args(['--setup'])
        assert args.setup == ''

    def test_parser_voice(self):
        parser = _build_parser()
        args = parser.parse_args(['-v', 'coral', 'hello'])
        assert args.voice == 'coral'

    def test_parser_format(self):
        parser = _build_parser()
        args = parser.parse_args(['--format', 'wav', 'hello'])
        assert args.format == 'wav'

    def test_parser_no_cache(self):
        parser = _build_parser()
        args = parser.parse_args(['--no-cache', 'hello'])
        assert args.no_cache is True

    def test_parser_cache_operations(self):
        parser = _build_parser()

        args = parser.parse_args(['--list-cached'])
        assert args.list_cached is True

        args = parser.parse_args(['-p'])
        assert args.prev is True

        args = parser.parse_args(['--cleanup'])
        assert args.cleanup is True


class TestMainKeyManagement:
    def test_setup_direct_key_json(self, tmp_path: Path, capsys):
        fake_dir = tmp_path / 'osay'
        fake_key_file = fake_dir / 'key.json'
        with (
            patch('osay.key.CONFIG_DIR', fake_dir),
            patch('osay.key.KEY_FILE', fake_key_file),
            patch('osay.cli.save_api_key', wraps=__import__('osay.key', fromlist=['save_api_key']).save_api_key),
            patch('sys.argv', ['osay', '--setup', 'sk-test-abc', '--json']),
        ):
            main()
        out = json.loads(capsys.readouterr().out)
        assert out['status'] == 'ok'

    def test_show_key_json_not_configured(self, tmp_path: Path, capsys):
        fake_key_file = tmp_path / 'key.json'
        with (
            patch('osay.key.KEY_FILE', fake_key_file),
            patch('osay.cli.ensure_api_key', return_value=None),
            patch.dict(os.environ, {}, clear=True),
            patch('sys.argv', ['osay', '--show-key', '--json']),
        ):
            os.environ.pop('OPENAI_API_KEY', None)
            main()
        out = json.loads(capsys.readouterr().out)
        assert out['configured'] is False

    def test_remove_key_json(self, tmp_path: Path, capsys):
        with (
            patch('osay.cli.remove_api_key', return_value=True),
            patch('sys.argv', ['osay', '--remove-key', '--json']),
        ):
            main()
        out = json.loads(capsys.readouterr().out)
        assert out['status'] == 'removed'


class TestMainNoInput:
    def test_no_text_tty_exits(self):
        with (
            patch('sys.argv', ['osay']),
            patch('sys.stdin') as mock_stdin,
            patch('osay.cli.ensure_api_key', return_value=None),
            patch('osay.cli._select_provider'),
            pytest.raises(SystemExit) as exc_info,
        ):
            mock_stdin.isatty.return_value = True
            main()
        assert exc_info.value.code == EXIT_NO_INPUT

    def test_no_text_tty_json(self, capsys):
        with (
            patch('sys.argv', ['osay', '--json']),
            patch('sys.stdin') as mock_stdin,
            patch('osay.cli.ensure_api_key', return_value=None),
            patch('osay.cli._select_provider'),
            pytest.raises(SystemExit) as exc_info,
        ):
            mock_stdin.isatty.return_value = True
            main()
        assert exc_info.value.code == EXIT_NO_INPUT
        out = json.loads(capsys.readouterr().out)
        assert out['error'] == 'no_input'


class TestMainCacheOperations:
    def test_list_cached_json_empty(self, capsys):
        with (
            patch('sys.argv', ['osay', '--list-cached', '--json']),
            patch('osay.cli.AudioCache') as mock_cache_cls,
        ):
            mock_cache_cls.return_value.list_cached.return_value = []
            main()
        out = json.loads(capsys.readouterr().out)
        assert out['items'] == []

    def test_cleanup_json(self, capsys):
        with (
            patch('sys.argv', ['osay', '--cleanup', '--json']),
            patch('osay.cli.AudioCache') as mock_cache_cls,
        ):
            mock_cache_cls.return_value.cleanup.return_value = 3
            main()
        out = json.loads(capsys.readouterr().out)
        assert out['status'] == 'ok'
        assert out['removed'] == 3
