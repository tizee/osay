"""Tests for osay.providers module."""

from unittest.mock import MagicMock, patch

import pytest

from osay.providers import MacOSsayProvider, OpenAITTSProvider


def _make_openai_provider() -> OpenAITTSProvider:
    """Create an OpenAITTSProvider with mocked clients."""
    with (
        patch('osay.providers.openai'),
        patch('osay.providers.AsyncOpenAI'),
    ):
        return OpenAITTSProvider(api_key='sk-test')


class TestOpenAITTSProvider:
    def test_invalid_voice_raises(self):
        provider = _make_openai_provider()
        with pytest.raises(ValueError, match='Invalid voice'):
            provider.synthesize('hello', voice='nonexistent')

    def test_invalid_format_raises(self):
        provider = _make_openai_provider()
        with pytest.raises(ValueError, match='Invalid format'):
            provider.synthesize('hello', response_format='xyz')

    def test_list_voices(self):
        provider = _make_openai_provider()
        voices = provider.list_voices()
        assert 'onyx' in voices
        assert 'coral' in voices
        assert len(voices) == 10

    def test_default_voice_is_onyx(self):
        assert OpenAITTSProvider.DEFAULT_VOICE == 'onyx'


class TestMacOSsayProvider:
    def test_synthesize_calls_say(self):
        provider = MacOSsayProvider()
        with patch('osay.providers.subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            provider.synthesize('hello', voice='Alex')
        mock_run.assert_called_once_with(
            ['say', '-v', 'Alex', 'hello'], check=True, capture_output=True, text=True
        )

    def test_synthesize_with_output_file(self):
        provider = MacOSsayProvider()
        with patch('osay.providers.subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            provider.synthesize('hello', output_file='/tmp/out.aiff')
        mock_run.assert_called_once_with(
            ['say', '-o', '/tmp/out.aiff', 'hello'], check=True, capture_output=True, text=True
        )

    def test_synthesize_command_not_found(self):
        provider = MacOSsayProvider()
        with (
            patch('osay.providers.subprocess.run', side_effect=FileNotFoundError),
            pytest.raises(RuntimeError, match='not found'),
        ):
            provider.synthesize('hello')

    def test_list_voices_returns_list(self):
        provider = MacOSsayProvider()
        mock_result = MagicMock()
        mock_result.stdout = 'Alex  en_US  # Hello\nSamantha  en_US  # Hi\n'
        with patch('osay.providers.subprocess.run', return_value=mock_result):
            voices = provider.list_voices()
        assert len(voices) == 2

    def test_list_voices_empty_on_error(self):
        provider = MacOSsayProvider()
        with patch('osay.providers.subprocess.run', side_effect=FileNotFoundError):
            assert provider.list_voices() == []
