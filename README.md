# osay - OpenAI Text-to-Speech CLI Tool

A powerful command-line text-to-speech tool that combines OpenAI's advanced TTS with macOS's built-in `say` command fallback.

## Features

- **OpenAI GPT-4o-mini-tts**: Latest AI-powered speech synthesis with natural intonation
- **10 AI Voices**: alloy, ash, ballad, coral, echo, fable, nova, onyx (default), sage, shimmer
- **Speech Instructions**: Control tone, emotion, speed, and speaking style
- **Multiple Formats**: MP3, WAV, Opus, AAC, FLAC, PCM
- **Live Streaming**: Real-time audio playback with `--no-cache` for lowest latency
- **Audio Caching**: Automatically caches generated audio for replay
- **macOS Fallback**: Automatically falls back to system `say` command if no API key
- **Voice Preview**: List voices with sample text and language information

## Installation

### Option 1: Using Make (Recommended)

The easiest way to install `osay` is using the included Makefile:

```bash
# Install to ~/.local/bin (default)
make install

# Install to /usr/local/bin (requires admin rights)
sudo make install PREFIX=/usr/local

# Verify installation
make check
```

**Note**: Make sure your installation directory (e.g., `~/.local/bin` or `/usr/local/bin`) is in your `PATH`. If not, add it to your shell config:

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
```

### Option 2: Manual Installation

If you prefer not to use `make`:

1. **Install uv** (if not already installed):
   ```bash
   brew install uv
   ```

2. **Make scripts executable**:
   ```bash
   chmod +x osay say.py
   ```

3. **Copy to PATH** (optional):
   ```bash
   sudo cp osay /usr/local/bin/
   sudo cp say.py /usr/local/bin/
   ```

### Uninstallation

```bash
# If installed with make
make uninstall

# If installed manually
sudo rm -f /usr/local/bin/osay /usr/local/bin/say.py
rm -rf ~/.config/osay  # Remove config directory
```

## Quick Start

### Setup OpenAI API Key

```bash
# Interactive setup
./osay --setup

# Or manually set environment variable
export OPENAI_API_KEY="sk-..."
```

### Basic Usage

```bash
# Speak text (uses OpenAI if key is set, otherwise macOS say)
./osay "Hello, world!"

# Use different voice
./osay -v coral "Hello with coral voice!"

# Save to audio file
./osay -o hello.mp3 "Save this speech"

# Read from file
./osay -f document.txt

# Pipe from stdin
./osay --instructions "Speak with excitement" -v fable "I'm so excited to tell you this!"

# Neutral speech (no cheerful default)
./osay --no-instructions "Just the facts"

# List all available voices
./osay -v '?'
```

## Audio Caching

Audio is cached by default for easy replay. Cache is stored in `~/.osay/audios/` (max 10 files).

```bash
# Play the most recent cached audio
./osay -p
./osay --prev

# List all cached audio files
./osay --list-cached

# Play cached audio by ID
./osay --play-cached abc123

# Select cached audio with fzf (interactive, requires fzf)
./osay --play-cached
```

> **Note**: Interactive selection requires [fzf](https://github.com/junegunn/fzf). Install with `brew install fzf`.

## Live Streaming

Use `--no-cache` for real-time audio streaming with the lowest possible latency. Audio plays as it's generated, without saving to disk.

```bash
# Stream audio in real-time (no caching)
./osay --no-cache "This plays immediately as it streams!"

# Great for interactive applications
./osay --no-cache --instructions "Speak quickly" "Fast response needed"

# Combine with different voices
./osay --no-cache -v coral "Real-time coral voice"
```

**How it works**: When `--no-cache` is used, audio streams directly from OpenAI's API using PCM format and plays through the built-in audio player. This eliminates file I/O overhead and provides the fastest time-to-first-audio.

## Advanced Features

### Speech Instructions

Control how the AI speaks with natural language instructions:

```bash
# Emotion and tone
./osay --instructions "Speak in a sad, melancholic tone" "I miss you"

# Speed and pacing
./osay --instructions "Speak very slowly and clearly" "This is important"

# Character impressions
./osay --instructions "Speak like a movie trailer narrator" "In a world..."

# Multi-lingual with accent
./osay --instructions "Speak English with a French accent" "Bonjour, comment allez-vous?"
```

### Audio Formats

Choose the right format for your use case:

```bash
# Low latency for real-time applications
./osay --format wav "Quick response"

# High quality lossless
./osay --format flac --output-file speech.flac "Studio quality"

# Optimized for streaming
./osay --format opus --output-file stream.opus "For web streaming"
```

### OpenAI-Only Features

These only work when OpenAI API key is configured:

- `--instructions` - Control speech style and emotion
- `--format` - Choose from 6 audio formats
- `--no-instructions` - Disable default cheerful tone
- `--no-cache` - Enable live streaming for lowest latency playback

### macOS Fallback Features

When falling back to macOS `say`:

- Supports 100+ system voices in multiple languages
- AI voice metadata and preview text
- M4A and AIFF output formats
- No API key required

## Examples

### Batch Processing

```bash
# Convert all .txt files to audio
for file in *.txt; do
  ./osay -f "$file" -o "${file%.txt}.mp3"
done
```

### Interactive Mode

```bash
# Interactive speech
while true; do
  read -p "What should I say? " text
  [[ -z "$text" ]] && break
  ./osay "$text"
done
```

### System Integration

```bash
# Add to ~/.zshrc for easy access
alias say='~/path/to/osay'

# Use in scripts
#!/bin/bash
./osay "Starting backup process..."
# ... do backup ...
./osay --instructions "Speak with satisfaction" "Backup completed successfully!"
```

## Management Commands

```bash
# Check API key status
./osay --show-key

# Reconfigure API key
./osay --setup

# Remove stored API key
./osay --remove-key

# Show help
./osay --help
./osay -h

# Cache management
./osay --list-cached    # List cached audio files
./osay -p               # Play most recent cached audio
./osay --play-cached    # Select and play with fzf (requires fzf)
```

## Configuration

- **API Key**: `~/.config/osay/config` (600 permissions for security)
- **Audio Cache**: `~/.osay/audios/` (stores up to 10 most recent audio files)

## Troubleshooting

### OpenAI API Errors
- Ensure API key is valid and has billing enabled
- Check rate limits at https://platform.openai.com/account/limits
- Use `--show-key` to verify key is configured

### macOS say Not Found
- Only works on macOS systems
- On Linux/Windows, OpenAI API key is required

### Audio Playback Issues
- **Live streaming** (`--no-cache`): Uses OpenAI's built-in audio player (cross-platform)
- **Cached playback**: Uses `afplay` on macOS (should be available on all macOS systems)
- For non-standard formats with caching, `ffplay` from FFmpeg may be needed

## API Documentation

For detailed information about OpenAI's Text-to-Speech capabilities, including voice options, audio formats, and API parameters, see the official documentation:

- [OpenAI Text-to-Speech Guide](https://platform.openai.com/docs/guides/text-to-speech)

## License

MIT - feel free to use and modify!
