# osay

CLI text-to-speech tool using OpenAI API with macOS `say` fallback.

## Features

- **OpenAI GPT-4o-mini-tts**: AI-powered speech synthesis with natural intonation
- **10 AI Voices**: alloy, ash, ballad, coral, echo, fable, nova, onyx (default), sage, shimmer
- **Speech Instructions**: Control tone, emotion, speed, and speaking style
- **Multiple Formats**: MP3, WAV, Opus, AAC, FLAC, PCM
- **Live Streaming**: Real-time audio playback with `--no-cache` for lowest latency
- **Audio Caching**: Automatically caches generated audio for replay
- **macOS Fallback**: Automatically falls back to system `say` command if no API key
- **JSON Output**: `--json` flag for machine-readable output (agent-friendly)

## Installation

### From source (recommended)

```bash
git clone <repo-url>
cd osay
uv sync
```

### As a global tool

```bash
uv tool install .
# or from the repo:
make install-tool
```

### Verify installation

```bash
osay --version
```

## Quick Start

### Setup OpenAI API Key

```bash
# Interactive setup
osay --setup

# Or pass key directly (useful for automation)
osay --setup sk-...

# Or set environment variable
export OPENAI_API_KEY="sk-..."
```

The API key is stored in `~/.config/osay/key.json` with restricted permissions (0600).

### Basic Usage

```bash
# Speak text
osay "Hello, world!"

# Use different voice
osay -v coral "Hello with coral voice!"

# Save to audio file
osay -o hello.mp3 "Save this speech"

# Read from file
osay -f document.txt

# Pipe from stdin
echo "Hello from a pipe" | osay

# Custom speech style
osay --instructions "Speak slowly and dramatically" "To be or not to be"

# Neutral speech (no cheerful default)
osay --no-instructions "Just the facts"

# List available voices
osay -v '?'
```

## Live Streaming

Use `--no-cache` for real-time audio streaming with the lowest latency:

```bash
osay --no-cache "This plays immediately as it streams!"
```

## Audio Caching

Audio is cached by default for easy replay in `~/.osay/audios/`.

```bash
osay -p                         # Play most recent
osay --list-cached              # List cached audio
osay --play-cached              # Select with fzf (interactive)
osay --play-cached abc123       # Play specific ID
osay --cleanup                  # Clean up expired cache
```

## JSON Output

Use `--json` for machine-readable output (useful for scripting and AI agents):

```bash
osay --list-cached --json
osay --show-key --json
osay --cleanup --json
osay --json "Hello world"
```

## Key Management

```bash
osay --setup              # Interactive setup
osay --setup sk-...       # Direct key (non-interactive)
osay --show-key           # Check key status
osay --remove-key         # Remove stored key
```

## Audio Formats

```bash
osay --format wav "High quality"
osay --format flac -o speech.flac "Lossless"
osay --format opus -o stream.opus "For streaming"
```

## Configuration

| File | Purpose |
|------|---------|
| `~/.config/osay/key.json` | API key (0600 permissions) |
| `~/.config/osay/config.json` | Settings (cache, cleanup, expiry) |
| `~/.osay/audios/` | Audio cache |

### config.json defaults

```json
{
  "audio_cache": true,
  "cleanup_enabled": true,
  "cache_expire_days": 30
}
```

## Development

```bash
# Install dependencies
uv sync

# Run tests
make test

# Lint & format
make lint
make fmt

# Type check
make typecheck
```

## License

MIT
