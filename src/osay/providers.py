"""TTS provider implementations."""

import asyncio
import subprocess
from abc import ABC, abstractmethod

import openai
from openai import AsyncOpenAI
from openai.helpers import LocalAudioPlayer


class TTSProvider(ABC):
    """Abstract base class for Text-to-Speech providers."""

    @abstractmethod
    def synthesize(
        self,
        text: str,
        output_file: str | None = None,
        voice: str | None = None,
        instructions: str | None = None,
        response_format: str | None = None,
    ) -> None:
        """Synthesize text to speech."""

    @abstractmethod
    def list_voices(self) -> list[str]:
        """List available voices."""


class OpenAITTSProvider(TTSProvider):
    """OpenAI Text-to-Speech provider using gpt-4o-mini-tts."""

    VOICES = [
        'alloy',
        'ash',
        'ballad',
        'coral',
        'echo',
        'fable',
        'nova',
        'onyx',
        'sage',
        'shimmer',
    ]
    DEFAULT_VOICE = 'onyx'

    AUDIO_FORMATS = {'mp3', 'opus', 'aac', 'flac', 'wav', 'pcm'}
    DEFAULT_FORMAT = 'mp3'

    def __init__(self, api_key: str | None = None) -> None:
        """Initialize with optional API key."""
        if api_key:
            openai.api_key = api_key
        self.client = openai.OpenAI()
        self.async_client = AsyncOpenAI()

    async def _stream_and_play(
        self, text: str, voice: str, instructions: str | None = None
    ) -> None:
        """Stream audio from OpenAI and play in real-time via LocalAudioPlayer."""
        kwargs: dict[str, str] = {
            'model': 'gpt-4o-mini-tts',
            'voice': voice,
            'input': text,
            'response_format': 'pcm',
        }
        if instructions:
            kwargs['instructions'] = instructions

        async with self.async_client.audio.speech.with_streaming_response.create(
            **kwargs  # pyright: ignore[reportArgumentType]
        ) as response:
            await LocalAudioPlayer().play(response)

    def synthesize(
        self,
        text: str,
        output_file: str | None = None,
        voice: str | None = None,
        instructions: str | None = None,
        response_format: str | None = None,
    ) -> None:
        """Synthesize text using OpenAI API."""
        if not voice:
            voice = self.DEFAULT_VOICE

        if voice not in self.VOICES:
            raise ValueError(f"Invalid voice '{voice}'. Available: {', '.join(self.VOICES)}")

        if not response_format:
            response_format = self.DEFAULT_FORMAT

        if response_format not in self.AUDIO_FORMATS:
            raise ValueError(
                f"Invalid format '{response_format}'. Available: {', '.join(sorted(self.AUDIO_FORMATS))}"
            )

        try:
            if output_file:
                kwargs: dict[str, str] = {
                    'model': 'gpt-4o-mini-tts',
                    'voice': voice,
                    'input': text,
                    'response_format': response_format,
                }
                if instructions:
                    kwargs['instructions'] = instructions

                with self.client.audio.speech.with_streaming_response.create(
                    **kwargs  # pyright: ignore[reportArgumentType]
                ) as response:
                    response.stream_to_file(output_file)
            else:
                asyncio.run(self._stream_and_play(text, voice, instructions))

        except openai.AuthenticationError:
            raise RuntimeError(
                'OpenAI API key is invalid or not set. Set OPENAI_API_KEY environment variable.'
            ) from None
        except Exception as e:
            raise RuntimeError(f'OpenAI API error: {e}') from e

    def list_voices(self) -> list[str]:
        """Return list of available OpenAI voices."""
        return list(self.VOICES)


class MacOSsayProvider(TTSProvider):
    """macOS 'say' command provider."""

    def synthesize(
        self,
        text: str,
        output_file: str | None = None,
        voice: str | None = None,
        instructions: str | None = None,
        response_format: str | None = None,
    ) -> None:
        """Synthesize text using macOS 'say' command."""
        cmd = ['say']

        if voice:
            cmd.extend(['-v', voice])

        if output_file:
            cmd.extend(['-o', output_file])

        cmd.append(text)

        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"macOS 'say' command failed: {e.stderr}") from e
        except FileNotFoundError:
            raise RuntimeError(
                "macOS 'say' command not found. This tool only works on macOS."
            ) from None

    def list_voices(self) -> list[str]:
        """List available macOS voices."""
        try:
            result = subprocess.run(['say', '-v', '?'], capture_output=True, text=True, check=True)
            return [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
        except (subprocess.CalledProcessError, FileNotFoundError):
            return []
