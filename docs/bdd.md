# osay BDD Test Specifications

Behavior-Driven Development specifications for osay. Each feature is
described using Given/When/Then format. These map to the test suite
in `tests/`.

---

## Feature: Text-to-Speech Synthesis

### Scenario: Speak text with default settings
```
Given an API key is configured
When the user runs `osay "Hello world"`
Then the text is synthesized using OpenAI gpt-4o-mini-tts
And the audio is played via afplay
And the audio file is cached in ~/.osay/audios/
And stderr shows the provider, mode, timing, and cache ID
And exit code is 0
```

### Scenario: Speak text with no API key (macOS fallback)
```
Given no API key is configured
When the user runs `osay "Hello world"`
Then the text is synthesized using macOS `say` command
And stderr shows "Using macOS 'say' command"
And exit code is 0
```

### Scenario: Speak with specific voice
```
Given an API key is configured
When the user runs `osay -v coral "Hello"`
Then the text is synthesized with voice "coral"
And the cache key includes voice "coral"
```

### Scenario: Speak with custom instructions
```
Given an API key is configured
When the user runs `osay --instructions "Speak sadly" "Goodbye"`
Then the synthesis request includes instructions "Speak sadly"
And the cache key includes those instructions
```

### Scenario: Speak with no instructions
```
Given an API key is configured
When the user runs `osay --no-instructions "Just facts"`
Then the synthesis request has no instructions
And the default cheerful instruction is not applied
```

### Scenario: Save to file instead of playing
```
Given an API key is configured
When the user runs `osay -o output.mp3 "Hello"`
Then the audio is written to output.mp3
And no audio is played
And the file is not cached (output file bypasses cache)
```

### Scenario: Read text from file
```
Given a file ~/text.txt containing "Hello from file"
When the user runs `osay -f ~/text.txt`
Then "Hello from file" is synthesized and played
```

### Scenario: Read text from stdin
```
Given stdin contains "Hello from pipe"
When the user runs `echo "Hello from pipe" | osay`
Then "Hello from pipe" is synthesized and played
```

### Scenario: No text provided (error)
```
Given stdin is a TTY (interactive terminal)
When the user runs `osay` with no arguments
Then stderr shows "Error: No text provided. Use 'osay <text>'..."
And exit code is 2
```

### Scenario: File not found (error)
```
When the user runs `osay -f nonexistent.txt`
Then stderr shows "Error: File 'nonexistent.txt' not found"
And exit code is 2
```

---

## Feature: Live Streaming

### Scenario: Stream without caching
```
Given an API key is configured
When the user runs `osay --no-cache "Quick response"`
Then audio streams in real-time via LocalAudioPlayer (PCM format)
And no file is written to the cache directory
And stderr shows "Mode: Live streaming (PCM format - lowest latency)"
```

---

## Feature: Content-Addressable Cache

### Scenario: Cache hit (same input)
```
Given "Hello" was previously synthesized with voice "onyx", format "mp3",
      and default instructions
And the cached audio file exists in ~/.osay/audios/
When the user runs `osay "Hello"` with the same parameters
Then the cached audio is played directly via afplay
And no API call is made
And stderr shows "Cache hit: <cache_id>"
```

### Scenario: Cache miss (different voice)
```
Given "Hello" was cached with voice "onyx"
When the user runs `osay -v coral "Hello"`
Then a new API call is made (different cache key)
And the result is cached under a different ID
```

### Scenario: Cache miss (different instructions)
```
Given "Hello" was cached with default instructions
When the user runs `osay --instructions "Speak sadly" "Hello"`
Then a new API call is made
```

### Scenario: Stale cache entry (audio file missing)
```
Given a metadata JSON exists for cache key X
But the corresponding audio file has been deleted
When lookup() is called for the same input
Then it returns None (cache miss)
And the orphan metadata JSON is deleted
```

### Scenario: Cache key is deterministic
```
Given text="hello", voice="onyx", fmt="mp3", instructions=None
When compute_cache_key() is called twice
Then both calls return the same 12-character hex string
```

### Scenario: List cached audio
```
Given 3 audio files are cached
When the user runs `osay --list-cached`
Then stderr shows all 3 entries with ID, time, voice, text preview
```

### Scenario: Play most recent cached audio
```
Given at least 1 audio file is cached
When the user runs `osay -p`
Then the most recently cached audio is played
```

### Scenario: Interactive cache selection with fzf
```
Given fzf is installed
And cached audio files exist
When the user runs `osay --play-cached` (no ID)
Then fzf launches with cache entries
And the selected entry is played
```

### Scenario: Cleanup expired cache
```
Given cached entries exist, some older than cache_expire_days
When the user runs `osay --cleanup`
Then expired entries (audio + metadata) are removed
And fresh entries are kept
And stderr shows "Cleaned up N cached audio file(s)."
```

---

## Feature: API Key Management

### Scenario: Interactive key setup
```
Given no API key is configured
When the user runs `osay --setup`
Then a getpass prompt appears for the key
And the key is saved to ~/.config/osay/key.json
And the file has 0600 permissions
```

### Scenario: Direct key setup (agent-friendly)
```
When the user runs `osay --setup sk-test123`
Then the key "sk-test123" is saved to key.json with 0600 permissions
And no interactive prompt appears
```

### Scenario: Show key status
```
Given an API key is stored in key.json
When the user runs `osay --show-key`
Then stderr shows the key source and first 8 characters
```

### Scenario: Remove stored key
```
Given key.json exists
When the user runs `osay --remove-key`
Then key.json is deleted
And stderr shows "API key removed."
```

### Scenario: Environment variable takes priority
```
Given OPENAI_API_KEY is set in the environment
And a different key is stored in key.json
When load_api_key() is called
Then the environment variable value is returned
```

---

## Feature: JSON Output Mode

### Scenario: Synthesis with --json
```
When the user runs `osay --json "Hello"`
Then stdout contains valid JSON with "status", "cache_hit", "elapsed_seconds"
And stderr still shows human-readable status (if TTY)
```

### Scenario: Cache hit with --json
```
Given "Hello" is cached
When the user runs `osay --json "Hello"`
Then stdout contains {"status":"ok","cache_hit":true,"id":"..."}
```

### Scenario: Error with --json
```
When the user runs `osay --json` with no text (TTY stdin)
Then stdout contains {"error":"no_input","message":"..."}
And exit code is 2
```

### Scenario: List cached with --json
```
When the user runs `osay --list-cached --json`
Then stdout contains {"items":[...]} with full metadata
```

### Scenario: Key management with --json
```
When the user runs `osay --show-key --json`
Then stdout contains {"configured":...,"source":...,"prefix":...}
```

---

## Feature: Configuration

### Scenario: Default configuration (no config file)
```
Given ~/.config/osay/config.json does not exist
When Config is loaded
Then audio_cache is True
And cleanup_enabled is True
And cache_expire_days is 30
```

### Scenario: Custom configuration
```
Given config.json contains {"audio_cache": false, "cache_expire_days": 7}
When Config is loaded
Then audio_cache is False
And cache_expire_days is 7
And cleanup_enabled is True (default, not overridden)
```

### Scenario: Corrupt config file
```
Given config.json contains invalid JSON
When Config is loaded
Then all defaults are used
And no error is raised
```

---

## Feature: Provider Validation

### Scenario: Invalid voice name
```
When OpenAITTSProvider.synthesize() is called with voice="nonexistent"
Then ValueError is raised with message listing available voices
```

### Scenario: Invalid audio format
```
When OpenAITTSProvider.synthesize() is called with response_format="xyz"
Then ValueError is raised with message listing available formats
```

### Scenario: macOS say not found
```
Given the `say` command is not on PATH
When MacOSsayProvider.synthesize() is called
Then RuntimeError is raised with "not found" message
```

---

## Feature: Version

### Scenario: Show version
```
When the user runs `osay --version`
Then stdout shows "osay 0.2.0"
And exit code is 0
```
