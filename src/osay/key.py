"""API key management for osay.

Stores the OpenAI API key in ~/.config/osay/key.json with restricted permissions (0600).
"""

import os
import sys
import json
import stat
from pathlib import Path

from osay.config import CONFIG_DIR

KEY_FILE = CONFIG_DIR / 'key.json'


def load_api_key() -> str | None:
    """Load API key from environment or key.json.

    Priority: OPENAI_API_KEY env var > key.json file.
    """
    env_key = os.environ.get('OPENAI_API_KEY')
    if env_key:
        return env_key

    if not KEY_FILE.exists():
        return None

    try:
        with open(KEY_FILE) as f:
            data: dict[str, str] = json.load(f)
        return data.get('OPENAI_API_KEY')
    except (json.JSONDecodeError, OSError):
        return None


def save_api_key(api_key: str) -> Path:
    """Save API key to key.json with 0600 permissions.

    Returns:
        Path to the key file.
    """
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    data = {'OPENAI_API_KEY': api_key}
    KEY_FILE.write_text(json.dumps(data, indent=2) + '\n')
    KEY_FILE.chmod(stat.S_IRUSR | stat.S_IWUSR)  # 0600
    return KEY_FILE


def remove_api_key() -> bool:
    """Remove stored API key.

    Returns:
        True if a key file was removed, False if none existed.
    """
    if KEY_FILE.exists():
        KEY_FILE.unlink()
        return True
    return False


def ensure_api_key() -> str | None:
    """Load API key, exporting to env if found in key.json.

    This makes the key available to the openai client library
    without passing it explicitly.

    Returns:
        The API key string, or None if not found.
    """
    key = load_api_key()
    if key:
        os.environ['OPENAI_API_KEY'] = key
    return key


def setup_api_key_interactive() -> bool:
    """Interactively prompt for API key and store it.

    Returns:
        True if key was saved successfully.
    """
    print('OpenAI API key not found.', file=sys.stderr)
    print('', file=sys.stderr)
    print('To use OpenAI text-to-speech, you need an API key.', file=sys.stderr)
    print('Get one from: https://platform.openai.com/api-keys', file=sys.stderr)
    print('', file=sys.stderr)

    try:
        import getpass

        api_key = getpass.getpass('Enter your OpenAI API key: ')
    except (EOFError, KeyboardInterrupt):
        print('', file=sys.stderr)
        return False

    if not api_key.strip():
        print('Error: API key cannot be empty.', file=sys.stderr)
        return False

    api_key = api_key.strip()
    path = save_api_key(api_key)
    print(f'API key saved to {path}', file=sys.stderr)
    os.environ['OPENAI_API_KEY'] = api_key
    return True


def show_key_status() -> None:
    """Print API key status to stderr."""
    env_key = os.environ.get('OPENAI_API_KEY')
    if env_key:
        print('OpenAI API key is set (from environment)', file=sys.stderr)
        print(f'Key starts with: {env_key[:8]}...', file=sys.stderr)
        return

    key = load_api_key()
    if key:
        print(f'OpenAI API key is set (from {KEY_FILE})', file=sys.stderr)
        print(f'Key starts with: {key[:8]}...', file=sys.stderr)
    else:
        print('No OpenAI API key configured', file=sys.stderr)
        print("Run 'osay --setup' to configure your API key", file=sys.stderr)
