# osay - OpenAI Text-to-Speech CLI Tool

A powerful command-line text-to-speech tool that combines OpenAI's advanced TTS with macOS's built-in `say` command fallback.

## Features

- **OpenAI GPT-4o-mini-tts**: Latest AI-powered speech synthesis with natural intonation
- **10 AI Voices**: alloy, ash, ballad, coral, echo, fable, nova, onyx (default), sage, shimmer
- **Speech Instructions**: Control tone, emotion, speed, and speaking style
- **Multiple Formats**: MP3, WAV, Opus, AAC, FLAC, PCM
- **Audio Caching**: Automatically caches generated audio for replay
- **macOS Fallback**: Automatically falls back to system `say` command if no API key
- **Voice Preview**: List voices with sample text and language information

## Installation

1. **Install uv** (if not already installed):
   ```bash
   brew install uv
   ```

2. **Make scripts executable**:
   ```bash
   chmod +x osay say.py
   ```

3. **Add to PATH** (optional):
   ```bash
   sudo cp osay /usr/local/bin/
   sudo cp say.py /usr/local/bin/
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

# Select cached audio with fzf (interactive)
./osay --play-cached

# Disable caching for a single command
./osay --no-cache "This won't be cached"
```

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
./osay --play-cached    # Select and play with fzf
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
- Ensure `afplay` is available (should be on all macOS)
- For non-standard formats, `ffplay` from FFmpeg may be needed

## License

MIT - feel free to use and modify!
