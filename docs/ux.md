# osay UX Design

## Design Principles

1. **Zero-config happy path** -- `osay "hello"` works out of the box with macOS
   `say`. Adding an API key upgrades to OpenAI TTS with no other changes.
2. **Stderr for humans, stdout for machines** -- status messages, mode
   indicators, and timing go to stderr. Only `--json` output and voice
   listings go to stdout. This means `osay "hello" > /dev/null` suppresses
   nothing visible; piping works naturally.
3. **Cache is invisible until you need it** -- caching is on by default, cache
   hits are silent unless you're watching stderr. `--no-cache` opts out
   completely for lowest latency.
4. **Agent-first, human-friendly** -- every operation has a `--json` mode.
   `--setup KEY` allows non-interactive key setup. Exit codes are
   meaningful and documented.

## Human UX

### First-Run Experience

```
$ osay "Hello world"
Using macOS 'say' command                           <- stderr
(macOS say plays audio)

$ osay --setup
OpenAI API key not found.                           <- stderr
To use OpenAI text-to-speech, you need an API key.
Get one from: https://platform.openai.com/api-keys
Enter your OpenAI API key: ********
API key saved to /Users/you/.config/osay/key.json

$ osay "Hello world"
Using OpenAI TTS (voices: alloy, ash, ...)          <- stderr
Mode: Cached playback (mp3 format)                  <- stderr
Completed in 1.23s                                  <- stderr
Cached audio ID: a1b2c3d4e5f6                       <- stderr
(audio plays)

$ osay "Hello world"
Cache hit: a1b2c3d4e5f6                             <- stderr
(audio plays instantly from cache)
```

### Feedback Model

All feedback goes to stderr so stdout stays clean for piping:

| Situation        | stderr message                        | Exit code |
|------------------|---------------------------------------|-----------|
| Provider chosen  | `Using OpenAI TTS (voices: ...)`      | -         |
| Playback mode    | `Mode: Cached playback (mp3 format)`  | -         |
| Cache hit        | `Cache hit: a1b2c3d4e5f6`             | 0         |
| Cache miss       | `Cached audio ID: a1b2c3d4e5f6`       | 0         |
| Timing           | `Completed in 1.23s`                  | -         |
| No text          | `Error: No text provided. Use ...`    | 2         |
| Bad API key      | `Error: OpenAI API key is invalid...` | 3         |
| Quiet mode       | (nothing -- non-TTY stderr)           | 0         |

### Quiet Mode

When stderr is not a TTY (e.g., piped), status messages are suppressed
automatically. No `--quiet` flag needed. This prevents log noise when
osay is called from scripts.

### Voice Discovery

```
$ osay -v '?'
Available voices:
  alloy
  ash
  ballad
  coral
  echo
  fable
  nova
  onyx
  sage
  shimmer
```

With JSON:

```
$ osay -v '?' --json
{
  "voices": ["alloy", "ash", "ballad", ...]
}
```

## Agent UX (AX)

### Structured Output

Every command supports `--json`. JSON goes to stdout, status to stderr.
Agents should always pass `--json`.

| Command                        | JSON stdout                                |
|--------------------------------|--------------------------------------------|
| `osay --json "hello"`          | `{"status":"ok","cache_hit":false,...}`     |
| `osay --json "hello"` (2nd)   | `{"status":"ok","cache_hit":true,"id":...}` |
| `osay --list-cached --json`    | `{"items":[...]}`                          |
| `osay --show-key --json`       | `{"configured":true,"source":"key.json"}`  |
| `osay --cleanup --json`        | `{"status":"ok","removed":3}`              |
| `osay --setup KEY --json`      | `{"status":"ok","key_file":"..."}`         |
| `osay --remove-key --json`     | `{"status":"removed"}`                     |
| (error)                        | `{"error":"no_input","message":"..."}`     |

### Non-Interactive Key Setup

Agents should use `osay --setup sk-... --json` instead of the interactive
prompt. The interactive prompt uses `getpass` which requires a TTY.

### Exit Codes

Agents should check exit codes before parsing stdout:

- `0` -- success, parse JSON
- `1` -- general error
- `2` -- no input (no text, file not found)
- `3` -- authentication error (bad/missing API key)

### Piping

```bash
# Text from another command
echo "status report" | osay --json

# Read from file
osay -f report.txt --json

# Save to file (no playback)
osay -o output.mp3 "hello" --json
```

### Cache Behavior for Agents

Agents benefit most from caching: repeated calls with the same text
(e.g., status announcements) hit cache instantly with no API cost.
The `cache_hit` field in JSON output lets agents know whether the
API was called.

To force a fresh synthesis (e.g., after changing instructions):

```bash
osay --no-cache --json "hello"
```

### Token Efficiency

- `--json` output is compact: typically 50-100 bytes per response
- `--list-cached --json` returns full metadata array for batch processing
- Voice listing with `--json` returns a flat array, no decoration
