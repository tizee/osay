#!/usr/bin/env -S uv run --script
#
# /// script
# requires-python = ">=3.12"
# dependencies = ["openai>=1.0.0"]
# ///
"""
A Python CLI tool for text-to-speech using OpenAI API with fallback to macOS 'say' command.
"""

import argparse
import json
import os
import subprocess
import sys
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path

import openai


class TTSProvider(ABC):
    """Abstract base class for Text-to-Speech providers."""

    @abstractmethod
    def synthesize(self, text: str, output_file: str = None, voice: str = None,
                   instructions: str = None, response_format: str = None) -> None:
        """Synthesize text to speech."""
        pass

    @abstractmethod
    def list_voices(self) -> list[str]:
        """List available voices."""
        pass


class OpenAITTSProvider(TTSProvider):
    """OpenAI Text-to-Speech provider."""

    # OpenAI TTS voices (gpt-4o-mini-tts model)
    VOICES = ["alloy", "ash", "ballad", "coral", "echo", "fable", "nova", "onyx", "sage", "shimmer"]
    DEFAULT_VOICE = "onyx"

    # Supported audio formats
    AUDIO_FORMATS = {
        "mp3": "mp3",
        "opus": "opus",
        "aac": "aac",
        "flac": "flac",
        "wav": "wav",
        "pcm": "pcm"
    }
    DEFAULT_FORMAT = "mp3"

    def __init__(self, api_key: str = None):
        """Initialize with optional API key."""
        if api_key:
            openai.api_key = api_key
        self.client = openai.OpenAI()

    def synthesize(self, text: str, output_file: str = None, voice: str = None,
                   instructions: str = None, response_format: str = None) -> None:
        """Synthesize text using OpenAI API."""
        if not voice:
            voice = self.DEFAULT_VOICE

        if voice not in self.VOICES:
            raise ValueError(f"Invalid voice '{voice}'. Available: {', '.join(self.VOICES)}")

        if not response_format:
            response_format = self.DEFAULT_FORMAT

        if response_format not in self.AUDIO_FORMATS:
            raise ValueError(f"Invalid format '{response_format}'. Available: {', '.join(self.AUDIO_FORMATS.keys())}")

        try:
            # Use the newer gpt-4o-mini-tts model with enhanced capabilities
            kwargs = {
                "model": "gpt-4o-mini-tts",
                "voice": voice,
                "input": text,
                "response_format": response_format
            }

            # Add instructions if provided (for controlling tone, emotion, etc.)
            if instructions:
                kwargs["instructions"] = instructions

            # Use the newer streaming API to avoid deprecation warning
            with self.client.audio.speech.with_streaming_response.create(**kwargs) as response:
                if output_file:
                    response.stream_to_file(output_file)
                else:
                    # Create temporary file and play it
                    import tempfile
                    suffix = f".{response_format}"
                    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                        tmp_path = tmp.name
                        response.stream_to_file(tmp_path)

                    try:
                        # Play the audio file using appropriate player
                        if response_format in ["wav", "pcm", "mp3", "aac"]:
                            # Use afplay for supported formats
                            subprocess.run(["afplay", tmp_path], check=True)
                        else:
                            # For other formats, try ffplay if available
                            try:
                                subprocess.run(["ffplay", "-autoexit", "-nodisp", tmp_path],
                                             check=True, capture_output=True)
                            except (subprocess.CalledProcessError, FileNotFoundError):
                                # Fallback to afplay
                                subprocess.run(["afplay", tmp_path], check=True)
                    finally:
                        # Clean up temp file
                        os.unlink(tmp_path)

        except openai.AuthenticationError:
            raise RuntimeError("OpenAI API key is invalid or not set. Set OPENAI_API_KEY environment variable.")
        except Exception as e:
            raise RuntimeError(f"OpenAI API error: {e}")

    def list_voices(self) -> list[str]:
        """Return list of available OpenAI voices."""
        return self.VOICES


class MacOSsayProvider(TTSProvider):
    """macOS 'say' command provider."""

    def synthesize(self, text: str, output_file: str = None, voice: str = None,
                   instructions: str = None, response_format: str = None) -> None:
        """Synthesize text using macOS 'say' command."""
        cmd = ["say"]

        if voice:
            cmd.extend(["-v", voice])

        if output_file:
            # For file output, determine format based on extension
            output_path = Path(output_file)
            if output_path.suffix.lower() == ".m4a":
                # Use -o for M4A format
                cmd.extend(["-o", output_file])
            else:
                # Default to AIFF for other extensions
                cmd.extend(["-o", output_file])

        cmd.append(text)

        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"macOS 'say' command failed: {e.stderr}")
        except FileNotFoundError:
            raise RuntimeError("macOS 'say' command not found. This tool only works on macOS.")

    def list_voices(self) -> list[str]:
        """List available macOS voices with their preview text."""
        try:
            result = subprocess.run(["say", "-v", "?"], capture_output=True, text=True, check=True)
            voices = []
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    voices.append(line.strip())
            return voices
        except (subprocess.CalledProcessError, FileNotFoundError):
            return []


class AudioCache:
    """Manages caching of audio files with metadata."""

    CACHE_DIR = Path.home() / ".osay" / "audios"
    MAX_CACHE_SIZE = 10

    def __init__(self):
        """Initialize cache directory."""
        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self._cleanup_old_files()

    def _cleanup_old_files(self):
        """Remove oldest files if cache exceeds MAX_CACHE_SIZE."""
        audio_files = sorted(
            self.CACHE_DIR.glob("*.json"),
            key=lambda f: f.stat().st_mtime,
            reverse=True
        )

        if len(audio_files) > self.MAX_CACHE_SIZE:
            # Remove oldest files
            for old_file in audio_files[self.MAX_CACHE_SIZE:]:
                metadata = self._load_metadata(old_file)
                if metadata:
                    # Remove audio file if it exists
                    audio_path = self.CACHE_DIR / metadata["audio_file"]
                    if audio_path.exists():
                        audio_path.unlink()
                # Remove metadata file
                old_file.unlink()

    def _load_metadata(self, metadata_file: Path) -> dict:
        """Load metadata from JSON file."""
        try:
            with open(metadata_file, 'r') as f:
                return json.load(f)
        except Exception:
            return None

    def generate_cache_path(self, format: str = "mp3") -> tuple[str, str]:
        """Generate a new cache path and ID for direct synthesis."""
        cache_id = str(uuid.uuid4())[:8]
        cached_audio_name = f"{cache_id}.{format}"
        cached_audio_path = self.CACHE_DIR / cached_audio_name
        return cache_id, str(cached_audio_path)

    def save_metadata(self, cache_id: str, text: str, voice: str, format: str,
                      provider: str, instructions: str = None) -> None:
        """Save metadata for an already-cached audio file."""
        timestamp = datetime.now().isoformat()
        cached_audio_name = f"{cache_id}.{format}"

        metadata = {
            "id": cache_id,
            "timestamp": timestamp,
            "text": text,
            "voice": voice,
            "format": format,
            "provider": provider,
            "instructions": instructions,
            "audio_file": cached_audio_name
        }

        metadata_file = self.CACHE_DIR / f"{cache_id}.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)

    def list_cached(self) -> list[dict]:
        """List all cached audio files with metadata."""
        cached_items = []
        metadata_files = sorted(
            self.CACHE_DIR.glob("*.json"),
            key=lambda f: f.stat().st_mtime,
            reverse=True
        )

        for metadata_file in metadata_files:
            metadata = self._load_metadata(metadata_file)
            if metadata:
                cached_items.append(metadata)

        return cached_items

    def get_by_id(self, cache_id: str) -> dict:
        """Get cached item by ID."""
        metadata_file = self.CACHE_DIR / f"{cache_id}.json"
        return self._load_metadata(metadata_file)

    def play(self, cache_id: str) -> bool:
        """Play cached audio file."""
        metadata = self.get_by_id(cache_id)
        if not metadata:
            return False

        audio_path = self.CACHE_DIR / metadata["audio_file"]
        if not audio_path.exists():
            return False

        # Play the audio file
        try:
            subprocess.run(["afplay", str(audio_path)], check=True)
            return True
        except subprocess.CalledProcessError:
            return False


class TTSService:
    """Main TTS service that manages provider selection and fallback."""

    def __init__(self):
        """Initialize TTS service with automatic provider selection."""
        self.provider = self._select_provider()
        self.cache = AudioCache()

    def _select_provider(self) -> TTSProvider:
        """Select the appropriate TTS provider based on availability."""
        # Check for OpenAI API key
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            try:
                provider = OpenAITTSProvider(api_key)
                # Test the API key
                openai.OpenAI().models.list()
                print(f"Using OpenAI TTS (voices: {', '.join(provider.list_voices())})", file=sys.stderr)
                return provider
            except Exception:
                print("OpenAI API key found but invalid, falling back to macOS 'say'", file=sys.stderr)

        # Fallback to macOS say
        print("Using macOS 'say' command", file=sys.stderr)
        return MacOSsayProvider()

    def synthesize(self, text: str, output_file: str = None, voice: str = None,
                   instructions: str = None, response_format: str = None,
                   cache: bool = False) -> None:
        """Synthesize text using the selected provider."""
        # Use provider's default voice if not specified
        if not voice and hasattr(self.provider, 'DEFAULT_VOICE'):
            voice = self.provider.DEFAULT_VOICE

        fmt = response_format or 'mp3'

        if output_file:
            # Just synthesize to file, no playback
            self.provider.synthesize(text, output_file, voice, instructions, response_format)
        elif cache:
            # Synthesize directly to cache, then play
            cache_id, cache_path = self.cache.generate_cache_path(fmt)
            self.provider.synthesize(text, cache_path, voice, instructions, response_format)
            # Play the cached audio
            subprocess.run(["afplay", cache_path], check=True)
            # Save metadata
            self.cache.save_metadata(
                cache_id=cache_id,
                text=text,
                voice=voice,
                format=fmt,
                provider=self.provider.__class__.__name__,
                instructions=instructions
            )
            print(f"Cached audio ID: {cache_id}", file=sys.stderr)
        else:
            # No caching - provider handles temp file and playback
            self.provider.synthesize(text, None, voice, instructions, response_format)

    def list_voices(self) -> list[str]:
        """List available voices for the selected provider."""
        return self.provider.list_voices()

    def list_cached_audio(self):
        """List cached audio files."""
        cached_items = self.cache.list_cached()
        if not cached_items:
            print("No cached audio files found.", file=sys.stderr)
            return

        for i, item in enumerate(cached_items, 1):
            print(f"\n{i}. ID: {item['id']}", file=sys.stderr)
            print(f"   Time: {item['timestamp']}", file=sys.stderr)
            print(f"   Voice: {item['voice']}", file=sys.stderr)
            print(f"   Text: {item['text'][:80]}...", file=sys.stderr)
            if item.get('instructions'):
                print(f"   Instructions: {item['instructions']}", file=sys.stderr)

    def play_cached(self, cache_id: str = None):
        """Play cached audio. If no ID, use fzf to select."""
        if not cache_id:
            # Use fzf to select from cached items
            if not command_exists('fzf'):
                print("Error: fzf is not installed. Install it or provide a cache ID.", file=sys.stderr)
                print("Install: brew install fzf", file=sys.stderr)
                return

            cached_items = self.cache.list_cached()
            if not cached_items:
                print("No cached audio files found.", file=sys.stderr)
                return

            # Prepare fzf input: ID<tab>timestamp - voice - text
            # Tab delimiter hides ID from display with --with-nth=2
            fzf_input = []
            for item in cached_items:
                time_str = datetime.fromisoformat(item['timestamp']).strftime('%Y-%m-%d %H:%M')
                voice = item['voice'] or 'default'
                text = item['text'].replace('\n', ' ')
                if len(text) > 128:
                    text = text[:125] + '...'
                fzf_input.append(f"{item['id']}\t{time_str} - {voice} - {text}")

            # Run fzf with tab delimiter, show only field 2 (hides ID)
            preview_cmd = 'jq -r ".text" ~/.osay/audios/"$(echo {} | cut -f1)".json 2>/dev/null'
            fzf_cmd = ['fzf', '-d', '\t', '--with-nth=2',
                      '--preview', preview_cmd,
                      '--preview-window', 'up:3:wrap']

            try:
                process = subprocess.Popen(
                    fzf_cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    text=True
                )
                stdout, _ = process.communicate('\n'.join(fzf_input))

                if process.returncode != 0:
                    return

                selected = stdout.strip()
                if selected:
                    cache_id = selected.split('\t')[0]
                else:
                    return
            except (subprocess.SubprocessError, OSError):
                return

        # Play the selected audio
        if self.cache.play(cache_id):
            print(f"Playing cached audio: {cache_id}", file=sys.stderr)
        else:
            print(f"Error: Could not play cached audio: {cache_id}", file=sys.stderr)


def command_exists(cmd):
    """Check if command exists."""
    return subprocess.run(['which', cmd], capture_output=True).returncode == 0


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="say.py",
        description="Convert text to speech using OpenAI API or macOS 'say' command"
    )

    parser.add_argument(
        "text",
        nargs="?",
        help="Text to speak (if not provided, reads from stdin or file)"
    )

    parser.add_argument(
        "-f", "--file",
        metavar="FILE",
        help="Read text from file"
    )

    parser.add_argument(
        "-o", "--output-file",
        metavar="FILE",
        help="Save audio to file instead of speaking"
    )

    parser.add_argument(
        "-v", "--voice",
        metavar="VOICE",
        help="Voice to use (use -v '?' to list available voices)"
    )

    parser.add_argument(
        "--instructions",
        metavar="INSTRUCTIONS",
        default="Speak in a cheerful and positive tone.",
        help="Instructions for speech style (OpenAI only: tone, emotion, speed, etc.)"
    )

    parser.add_argument(
        "--no-instructions",
        action="store_true",
        help="Disable default instructions for neutral speech"
    )

    parser.add_argument(
        "--format",
        metavar="FORMAT",
        choices=["mp3", "opus", "aac", "flac", "wav", "pcm"],
        default="mp3",
        help="Audio output format (OpenAI only: mp3, opus, aac, flac, wav, pcm)"
    )

    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable caching of audio file"
    )

    parser.add_argument(
        "--list-cached",
        action="store_true",
        help="List cached audio files"
    )

    parser.add_argument(
        "--play-cached",
        metavar="ID",
        nargs="?",
        const="",
        help="Play cached audio (use without ID to select with fzf)"
    )

    parser.add_argument(
        "-p", "--prev",
        action="store_true",
        help="Play the most recent cached audio"
    )

    args = parser.parse_args()

    # Handle cached audio operations first (no API key needed)
    if args.list_cached:
        cache = AudioCache()
        cached_items = cache.list_cached()
        if not cached_items:
            print("No cached audio files found.", file=sys.stderr)
            return
        for i, item in enumerate(cached_items, 1):
            print(f"\n{i}. ID: {item['id']}", file=sys.stderr)
            print(f"   Time: {item['timestamp']}", file=sys.stderr)
            print(f"   Voice: {item['voice']}", file=sys.stderr)
            text_preview = item['text'][:80] + '...' if len(item['text']) > 80 else item['text']
            print(f"   Text: {text_preview}", file=sys.stderr)
            if item.get('instructions'):
                print(f"   Instructions: {item['instructions']}", file=sys.stderr)
        return

    if args.prev:
        cache = AudioCache()
        cached_items = cache.list_cached()
        if not cached_items:
            print("No cached audio files found. Generate some audio first!", file=sys.stderr)
            return
        latest = cached_items[0]
        print(f"Playing: {latest['text'][:60]}{'...' if len(latest['text']) > 60 else ''}", file=sys.stderr)
        cache.play(latest['id'])
        return

    if args.play_cached is not None:
        cache = AudioCache()
        cached_items = cache.list_cached()
        if not cached_items:
            print("No cached audio files found. Generate some audio first!", file=sys.stderr)
            return
        tts = TTSService.__new__(TTSService)
        tts.cache = cache
        tts.play_cached(args.play_cached if args.play_cached else None)
        return

    # Initialize TTS service (loads API key)
    tts = TTSService()

    # Validate format with macOS fallback
    if args.format != "mp3" and not isinstance(tts.provider, OpenAITTSProvider):
        print("Warning: Audio format option only works with OpenAI TTS. Using default format.", file=sys.stderr)

    # Handle voice listing
    if args.voice == "?":
        voices = tts.list_voices()
        print("Available voices:")
        for voice in voices:
            print(f"  {voice}")
        return

    # Determine instructions to use
    instructions = args.instructions
    if args.no_instructions:
        instructions = None

    # Get text to speak
    text = None
    if args.text:
        text = args.text
    elif args.file:
        try:
            with open(args.file, 'r', encoding='utf-8') as f:
                text = f.read().strip()
        except FileNotFoundError:
            print(f"Error: File '{args.file}' not found", file=sys.stderr)
            sys.exit(1)
    else:
        # Read from stdin
        if sys.stdin.isatty():
            print("Error: No text provided. Use 'say.py <text>', 'say.py -f <file>', or pipe text to stdin.", file=sys.stderr)
            sys.exit(1)
        text = sys.stdin.read().strip()

    if not text:
        print("Error: No text to speak", file=sys.stderr)
        sys.exit(1)

    # Synthesize speech
    try:
        tts.synthesize(text, args.output_file, args.voice, instructions, args.format, not args.no_cache)
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
