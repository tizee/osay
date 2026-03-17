# osay Design Document

## Overview

osay is a CLI text-to-speech tool that synthesizes speech via OpenAI's
gpt-4o-mini-tts API with automatic fallback to macOS's built-in `say` command.
It features content-addressable audio caching, streaming playback, and
structured JSON output for agent consumption.

## Architecture

```
src/osay/
  __init__.py      version constant
  __main__.py      python -m osay entry
  cli.py           argparse, main(), dispatch logic
  providers.py     TTSProvider ABC + OpenAI / macOS implementations
  cache.py         content-addressable AudioCache (SHA-256 keyed)
  config.py        config.json loader (~/.config/osay/config.json)
  key.py           API key management (~/.config/osay/key.json, 0600)
```

## CLI Flow

```
                         osay <args>
                             |
                     +-------+-------+
                     | parse argv    |
                     +-------+-------+
                             |
              +--------------+--------------+
              |              |              |
         key mgmt      cache ops       synthesis
         --setup       --list-cached      |
         --show-key    --play-cached      |
         --remove-key  --prev             |
                       --cleanup          |
                                          |
                               +----------+----------+
                               | ensure_api_key()    |
                               | _select_provider()  |
                               +----------+----------+
                                          |
                              +-----------+-----------+
                              | resolve text input    |
                              | (arg / -f / stdin)    |
                              +-----------+-----------+
                                          |
                              +-----------+-----------+
                              | resolve voice         |
                              | (arg or DEFAULT_VOICE)|
                              +-----------+-----------+
                                          |
                         +----------------+----------------+
                         |                |                |
                    -o <file>       cache enabled     --no-cache
                         |                |                |
                    synthesize      +-----+-----+     synthesize
                    to file         | lookup()  |     stream+play
                                    +-----+-----+     (no file)
                                          |
                                    +-----+-----+
                                    |  HIT?     |
                                    +--+-----+--+
                                   yes |     | no
                                       |     |
                                  afplay   synthesize
                                  cached   to cache path
                                  file     afplay
                                           save_metadata()
                                           auto_cleanup()
```

## Provider Selection

```
  ensure_api_key()
        |
  OPENAI_API_KEY in env?
   yes /       \ no
      /         \
 load key.json   |
 export to env   |
      |          |
  key available? |
   yes /    \ no |
      /      \   |
  validate    \  |
  via API      \ |
   ok / \ fail  \|
     /   \       |
 OpenAI   MacOSsayProvider
 TTSProvider
```

## Content-Addressable Cache

The cache uses SHA-256 hashes of `(text, voice, format, instructions)` as
file names, making lookup O(1) instead of scanning all metadata files.

```
  cache_key = sha256(text + \0 + voice + \0 + fmt + \0 + instructions)[:12]

  ~/.osay/audios/
    {cache_key}.mp3       audio file
    {cache_key}.json      metadata (id, timestamp, text, voice, ...)
```

### Cache Lifecycle

```
  Input: (text, voice, fmt, instructions)
                    |
            compute_cache_key()
                    |
              lookup()
            /       \
         HIT       MISS
          |          |
     return       generate_cache_path()
     metadata        |
                  synthesize to path
                     |
                  save_metadata()
                     |
                  auto_cleanup()
                  (remove entries older
                   than cache_expire_days)
```

### Stale Entry Handling

If metadata JSON exists but the audio file is missing (e.g., manually deleted),
`lookup()` treats it as a miss and removes the orphan metadata file. The cache
self-heals.

## Key Storage

```
  ~/.config/osay/
    key.json        {"OPENAI_API_KEY": "sk-..."}   permissions: 0600
    config.json     {"audio_cache": true, ...}     permissions: default
```

Key resolution priority:
1. `OPENAI_API_KEY` environment variable
2. `~/.config/osay/key.json` file

The `--setup` flag supports both interactive (getpass prompt) and direct
(`--setup sk-...`) modes. Direct mode is agent-friendly -- no TTY required.

## Exit Codes

| Code | Constant       | Meaning                            |
|------|----------------|------------------------------------|
| 0    | EXIT_OK        | Success                            |
| 1    | EXIT_ERROR     | General error                      |
| 2    | EXIT_NO_INPUT  | No text provided / file not found  |
| 3    | EXIT_AUTH_ERROR | API key invalid or missing         |

## JSON Output Mode

When `--json` is passed, all structured output goes to stdout as JSON.
Human-readable status messages still go to stderr. Error responses
are also JSON:

```json
{"error": "no_input", "message": "No text provided. Use ..."}
```

Successful synthesis:

```json
{"status": "ok", "cache_hit": false, "elapsed_seconds": 1.23}
```

Cache hit:

```json
{"status": "ok", "cache_hit": true, "id": "a1b2c3d4e5f6"}
```

## Playback Modes

| Mode            | Trigger                  | Latency | Caches? |
|-----------------|--------------------------|---------|---------|
| Live streaming  | `--no-cache`             | Lowest  | No      |
| Cached playback | default (cache enabled)  | Medium  | Yes     |
| File output     | `-o <file>`              | N/A     | No      |
| Cache hit       | same input, cache exists | Instant | N/A     |

Live streaming uses PCM format via `LocalAudioPlayer` for lowest
time-to-first-audio. Cached playback synthesizes to an mp3 file
then plays via `afplay`.
