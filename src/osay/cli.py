"""CLI entry point for osay."""

import os
import sys
import json
import time
import argparse
import subprocess
from typing import Any
from pathlib import Path
from datetime import datetime

import osay
from osay.key import (
    save_api_key,
    ensure_api_key,
    remove_api_key,
    show_key_status,
    setup_api_key_interactive,
)
from osay.cache import CACHE_DIR, AudioCache
from osay.config import Config
from osay.providers import TTSProvider, MacOSsayProvider, OpenAITTSProvider

# Exit codes
EXIT_OK = 0
EXIT_ERROR = 1
EXIT_NO_INPUT = 2
EXIT_AUTH_ERROR = 3


def _command_exists(cmd: str) -> bool:
    """Check if a command exists on PATH."""
    return subprocess.run(['which', cmd], capture_output=True).returncode == 0


def _select_provider(*, quiet: bool = False) -> TTSProvider:
    """Select TTS provider based on available API key."""
    import openai as _openai

    api_key = os.environ.get('OPENAI_API_KEY')
    if api_key:
        try:
            provider = OpenAITTSProvider(api_key)
            _openai.OpenAI().models.list()
            if not quiet:
                print(
                    f'Using OpenAI TTS (voices: {", ".join(provider.list_voices())})',
                    file=sys.stderr,
                )
            return provider
        except Exception:  # noqa: BLE001
            if not quiet:
                print(
                    "OpenAI API key found but invalid, falling back to macOS 'say'",
                    file=sys.stderr,
                )

    if not quiet:
        print("Using macOS 'say' command", file=sys.stderr)
    return MacOSsayProvider()


def _play_cached_audio(cache: AudioCache, cache_id: str | None = None) -> None:
    """Play cached audio. If no ID, select interactively with fzf."""
    if not cache_id:
        if not _command_exists('fzf'):
            print('Error: fzf is not installed. Install it or provide a cache ID.', file=sys.stderr)
            print('Install: brew install fzf', file=sys.stderr)
            return

        cached_items = cache.list_cached()
        if not cached_items:
            print('No cached audio files found.', file=sys.stderr)
            return

        fzf_input: list[str] = []
        for item in cached_items:
            time_str = datetime.fromisoformat(item['timestamp']).strftime('%Y-%m-%d %H:%M')
            voice = item['voice'] or 'default'
            text = item['text'].replace('\n', ' ')
            if len(text) > 128:
                text = text[:125] + '...'
            fzf_input.append(f'{item["id"]}\t{time_str} - {voice} - {text}')

        preview_cmd = f'jq -r ".text" {CACHE_DIR}/"$(echo {{}} | cut -f1)".json 2>/dev/null'
        fzf_cmd = [
            'fzf',
            '-d',
            '\t',
            '--with-nth=2',
            '--preview',
            preview_cmd,
            '--preview-window',
            'up:3:wrap',
        ]

        try:
            process = subprocess.Popen(
                fzf_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True
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

    if cache.play(cache_id):
        print(f'Playing cached audio: {cache_id}', file=sys.stderr)
    else:
        print(f'Error: Could not play cached audio: {cache_id}', file=sys.stderr)


def _build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog='osay',
        description='Text-to-speech using OpenAI API or macOS say',
    )

    parser.add_argument('text', nargs='?', help='Text to speak')
    parser.add_argument('-f', '--file', metavar='FILE', help='Read text from file')
    parser.add_argument(
        '-o', '--output-file', metavar='FILE', help='Save audio to file instead of speaking'
    )
    parser.add_argument('-v', '--voice', metavar='VOICE', help="Voice to use (use -v '?' to list)")
    parser.add_argument(
        '--instructions',
        metavar='TEXT',
        default='Speak in a cheerful and positive tone.',
        help='Instructions for speech style (OpenAI only)',
    )
    parser.add_argument(
        '--no-instructions', action='store_true', help='Disable default instructions'
    )
    parser.add_argument(
        '--format',
        metavar='FORMAT',
        choices=['mp3', 'opus', 'aac', 'flac', 'wav', 'pcm'],
        default='mp3',
        help='Audio output format (default: mp3)',
    )
    parser.add_argument(
        '--no-cache', action='store_true', help='Disable caching, use live streaming'
    )

    # Cache operations
    parser.add_argument('--list-cached', action='store_true', help='List cached audio files')
    parser.add_argument(
        '--play-cached',
        metavar='ID',
        nargs='?',
        const='',
        help='Play cached audio (no ID = fzf select)',
    )
    parser.add_argument('-p', '--prev', action='store_true', help='Play most recent cached audio')
    parser.add_argument(
        '--cleanup', action='store_true', help='Clean up expired cached audio files'
    )

    # Key management (ported from bash wrapper)
    parser.add_argument(
        '--setup',
        nargs='?',
        const='',
        metavar='KEY',
        help='Setup OpenAI API key (interactive or pass key directly)',
    )
    parser.add_argument('--show-key', action='store_true', help='Show API key status')
    parser.add_argument('--remove-key', action='store_true', help='Remove stored API key')

    # Meta
    parser.add_argument('--version', action='version', version=f'osay {osay.__version__}')
    parser.add_argument(
        '--json',
        action='store_true',
        dest='json_output',
        help='Output in JSON format (for machine consumption)',
    )

    return parser


def _json_out(data: dict[str, Any]) -> None:
    """Print JSON to stdout."""
    print(json.dumps(data, indent=2))


def main() -> None:
    """CLI entry point."""
    parser = _build_parser()
    args = parser.parse_args()

    json_mode: bool = args.json_output

    # --- Key management ---
    if args.setup is not None:
        if args.setup:
            # Direct key: osay --setup sk-...
            path = save_api_key(args.setup)
            if json_mode:
                _json_out({'status': 'ok', 'key_file': str(path)})
            else:
                print(f'API key saved to {path}', file=sys.stderr)
        else:
            # Interactive
            ok = setup_api_key_interactive()
            if json_mode:
                _json_out({'status': 'ok' if ok else 'cancelled'})
            elif not ok:
                sys.exit(EXIT_ERROR)
        return

    if args.show_key:
        if json_mode:
            key = ensure_api_key()
            _json_out(
                {
                    'configured': key is not None,
                    'source': 'environment' if os.environ.get('OPENAI_API_KEY') else 'key.json',
                    'prefix': key[:8] + '...' if key else None,
                }
            )
        else:
            show_key_status()
        return

    if args.remove_key:
        removed = remove_api_key()
        if json_mode:
            _json_out({'status': 'removed' if removed else 'not_found'})
        else:
            if removed:
                print('API key removed.', file=sys.stderr)
            else:
                print('No API key found to remove.', file=sys.stderr)
        return

    # --- Cache operations (no API key needed) ---
    if args.list_cached:
        cache = AudioCache()
        cached_items = cache.list_cached()
        if json_mode:
            _json_out({'items': cached_items})
        elif not cached_items:
            print('No cached audio files found.', file=sys.stderr)
        else:
            for i, item in enumerate(cached_items, 1):
                print(f'\n{i}. ID: {item["id"]}', file=sys.stderr)
                print(f'   Time: {item["timestamp"]}', file=sys.stderr)
                print(f'   Voice: {item["voice"]}', file=sys.stderr)
                text_preview = item['text'][:80] + '...' if len(item['text']) > 80 else item['text']
                print(f'   Text: {text_preview}', file=sys.stderr)
                if item.get('instructions'):
                    print(f'   Instructions: {item["instructions"]}', file=sys.stderr)
        return

    if args.prev:
        cache = AudioCache()
        cached_items = cache.list_cached()
        if not cached_items:
            if json_mode:
                _json_out({'error': 'no_cached_audio', 'message': 'No cached audio files found.'})
            else:
                print('No cached audio files found.', file=sys.stderr)
            sys.exit(EXIT_ERROR)
        latest = cached_items[-1]
        if not json_mode:
            text_preview = latest['text'][:60] + ('...' if len(latest['text']) > 60 else '')
            print(f'Playing: {text_preview}', file=sys.stderr)
        cache.play(latest['id'])
        if json_mode:
            _json_out({'status': 'played', 'id': latest['id']})
        return

    if args.play_cached is not None:
        cache = AudioCache()
        _play_cached_audio(cache, args.play_cached if args.play_cached else None)
        return

    if args.cleanup:
        cache = AudioCache()
        removed = cache.cleanup()
        if json_mode:
            _json_out({'status': 'ok', 'removed': removed})
        else:
            print(f'Cleaned up {removed} cached audio file(s).', file=sys.stderr)
        return

    # --- TTS synthesis ---
    quiet = not sys.stderr.isatty()
    ensure_api_key()
    provider = _select_provider(quiet=quiet)

    # Validate format with macOS fallback
    if args.format != 'mp3' and not isinstance(provider, OpenAITTSProvider) and not json_mode:
        print('Warning: Audio format option only works with OpenAI TTS.', file=sys.stderr)

    # Voice listing
    if args.voice == '?':
        voices = provider.list_voices()
        if json_mode:
            _json_out({'voices': voices})
        else:
            print('Available voices:')
            for voice in voices:
                print(f'  {voice}')
        return

    # Instructions
    instructions: str | None = args.instructions
    if args.no_instructions:
        instructions = None

    # Get text
    text: str | None = None
    if args.text:
        text = args.text
    elif args.file:
        try:
            text = Path(args.file).read_text(encoding='utf-8').strip()
        except FileNotFoundError:
            msg = f"File '{args.file}' not found"
            if json_mode:
                _json_out({'error': 'file_not_found', 'message': msg})
            else:
                print(f'Error: {msg}', file=sys.stderr)
            sys.exit(EXIT_NO_INPUT)
    else:
        if sys.stdin.isatty():
            msg = "No text provided. Use 'osay <text>', 'osay -f <file>', or pipe text to stdin."
            if json_mode:
                _json_out({'error': 'no_input', 'message': msg})
            else:
                print(f'Error: {msg}', file=sys.stderr)
            sys.exit(EXIT_NO_INPUT)
        text = sys.stdin.read().strip()

    if not text:
        msg = 'No text to speak'
        if json_mode:
            _json_out({'error': 'empty_input', 'message': msg})
        else:
            print(f'Error: {msg}', file=sys.stderr)
        sys.exit(EXIT_NO_INPUT)

    # Cache setting
    config = Config()
    use_cache = not args.no_cache and config.audio_cache_enabled

    fmt = args.format or 'mp3'
    voice = args.voice or getattr(provider, 'DEFAULT_VOICE', 'default')

    # Initialize cache once if enabled
    cache: AudioCache | None = None
    if use_cache:
        cache = AudioCache(
            cleanup_enabled=config.cleanup_enabled if config.audio_cache_enabled else None,
            cache_expire_days=config.cache_expire_days if config.audio_cache_enabled else None,
        )

    # Check cache hit before synthesizing
    if cache is not None and not args.output_file:
        hit = cache.lookup(text, voice, fmt, instructions)
        if hit:
            audio_path = CACHE_DIR / hit['audio_file']
            if not quiet:
                print(f'Cache hit: {hit["id"]}', file=sys.stderr)
            subprocess.run(['afplay', str(audio_path)], check=True)
            if json_mode:
                _json_out({'status': 'ok', 'cache_hit': True, 'id': hit['id']})
            return

    # Display playback mode
    if isinstance(provider, OpenAITTSProvider) and not quiet:
        if args.output_file:
            print(f'Mode: File output ({fmt} format)', file=sys.stderr)
        elif use_cache:
            print(f'Mode: Cached playback ({fmt} format)', file=sys.stderr)
        else:
            print('Mode: Live streaming (PCM format - lowest latency)', file=sys.stderr)

    # Synthesize
    start_time = time.time()

    try:
        if args.output_file:
            provider.synthesize(text, args.output_file, voice, instructions, args.format)
        elif cache is not None:
            cache_id, cache_path = cache.generate_cache_path(text, voice, fmt, instructions)
            provider.synthesize(text, cache_path, voice, instructions, args.format)
            subprocess.run(['afplay', cache_path], check=True)
            cache.save_metadata(
                cache_id=cache_id,
                text=text,
                voice=voice,
                fmt=fmt,
                provider=provider.__class__.__name__,
                instructions=instructions,
            )
            cache.auto_cleanup()
            if not quiet:
                print(f'Cached audio ID: {cache_id}', file=sys.stderr)
        else:
            provider.synthesize(text, None, voice, instructions, args.format)
    except RuntimeError as e:
        msg = str(e)
        if json_mode:
            _json_out({'error': 'synthesis_error', 'message': msg})
        else:
            print(f'Error: {msg}', file=sys.stderr)
        exit_code = EXIT_AUTH_ERROR if 'API key' in msg else EXIT_ERROR
        sys.exit(exit_code)

    elapsed = time.time() - start_time

    if isinstance(provider, OpenAITTSProvider) and not quiet:
        if use_cache or args.output_file:
            print(f'Completed in {elapsed:.2f}s', file=sys.stderr)
        else:
            print(f'Streamed in {elapsed:.2f}s (live playback)', file=sys.stderr)

    if json_mode:
        result: dict[str, Any] = {
            'status': 'ok',
            'cache_hit': False,
            'elapsed_seconds': round(elapsed, 2),
        }
        if args.output_file:
            result['output_file'] = args.output_file
        _json_out(result)
