"""Audio cache management for osay."""

import json
import hashlib
import subprocess
from typing import Any
from pathlib import Path
from datetime import datetime

CACHE_DIR = Path.home() / '.osay' / 'audios'


class AudioCache:
    """Manages caching of audio files with metadata."""

    def __init__(
        self,
        cleanup_enabled: bool | None = None,
        cache_expire_days: int | None = None,
    ) -> None:
        """Initialize cache directory."""
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self._cleanup_enabled = cleanup_enabled
        self._cache_expire_days = cache_expire_days

    @property
    def cleanup_enabled(self) -> bool:
        """Check if automatic cleanup is enabled."""
        if self._cleanup_enabled is not None:
            return self._cleanup_enabled
        from osay.config import Config

        return Config().cleanup_enabled

    @property
    def cache_expire_days(self) -> int:
        """Get cache expiration in days."""
        if self._cache_expire_days is not None:
            return self._cache_expire_days
        from osay.config import Config

        return Config().cache_expire_days

    def cleanup(self) -> int:
        """Remove expired cache files.

        Returns:
            Number of files removed.
        """
        expire_days = self.cache_expire_days
        removed_count = 0

        for metadata_file in CACHE_DIR.glob('*.json'):
            metadata = self._load_metadata(metadata_file)
            if not metadata:
                continue

            try:
                timestamp = datetime.fromisoformat(metadata['timestamp'])
                age_days = (datetime.now() - timestamp).days
                if age_days > expire_days:
                    self._remove_cached(metadata, metadata_file)
                    removed_count += 1
            except (KeyError, ValueError):
                self._remove_cached(metadata, metadata_file)
                removed_count += 1

        return removed_count

    def auto_cleanup(self) -> None:
        """Run cleanup if enabled (called after caching)."""
        if self.cleanup_enabled:
            self.cleanup()

    def _remove_cached(self, metadata: dict[str, Any], metadata_file: Path) -> None:
        """Remove a cached audio file and its metadata."""
        audio_name = metadata.get('audio_file', '')
        if audio_name:
            audio_path = CACHE_DIR / audio_name
            if audio_path.exists():
                audio_path.unlink()
        metadata_file.unlink()

    def _load_metadata(self, metadata_file: Path) -> dict[str, Any] | None:
        """Load metadata from a JSON file."""
        try:
            with open(metadata_file) as f:
                result: dict[str, Any] = json.load(f)
                return result
        except Exception:  # noqa: BLE001
            return None

    @staticmethod
    def compute_cache_key(
        text: str,
        voice: str,
        fmt: str,
        instructions: str | None = None,
    ) -> str:
        """Compute a deterministic cache key from synthesis parameters.

        Returns:
            First 12 hex chars of SHA-256 hash.
        """
        parts = f'{text}\x00{voice}\x00{fmt}\x00{instructions or ""}'
        return hashlib.sha256(parts.encode()).hexdigest()[:12]

    def lookup(
        self,
        text: str,
        voice: str,
        fmt: str,
        instructions: str | None = None,
    ) -> dict[str, Any] | None:
        """Look up a cached entry by input parameters.

        Returns:
            Metadata dict if cache hit and audio file exists, None otherwise.
        """
        cache_key = self.compute_cache_key(text, voice, fmt, instructions)
        metadata_file = CACHE_DIR / f'{cache_key}.json'
        metadata = self._load_metadata(metadata_file)
        if not metadata:
            return None
        audio_path = CACHE_DIR / metadata.get('audio_file', '')
        if not audio_path.exists():
            # Stale metadata -- audio file missing
            metadata_file.unlink(missing_ok=True)
            return None
        return metadata

    def generate_cache_path(
        self,
        text: str,
        voice: str,
        fmt: str = 'mp3',
        instructions: str | None = None,
    ) -> tuple[str, str]:
        """Generate a cache path based on input parameters.

        Returns:
            Tuple of (cache_key, file_path).
        """
        cache_key = self.compute_cache_key(text, voice, fmt, instructions)
        cached_audio_path = CACHE_DIR / f'{cache_key}.{fmt}'
        return cache_key, str(cached_audio_path)

    def save_metadata(
        self,
        cache_id: str,
        text: str,
        voice: str,
        fmt: str,
        provider: str,
        instructions: str | None = None,
    ) -> None:
        """Save metadata for a cached audio file."""
        metadata = {
            'id': cache_id,
            'timestamp': datetime.now().isoformat(),
            'text': text,
            'voice': voice,
            'format': fmt,
            'provider': provider,
            'instructions': instructions,
            'audio_file': f'{cache_id}.{fmt}',
        }

        metadata_file = CACHE_DIR / f'{cache_id}.json'
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)

    def list_cached(self) -> list[dict[str, Any]]:
        """List all cached audio files with metadata, sorted by time."""
        cached_items: list[dict[str, Any]] = []
        metadata_files = sorted(CACHE_DIR.glob('*.json'), key=lambda f: f.stat().st_mtime)

        for metadata_file in metadata_files:
            metadata = self._load_metadata(metadata_file)
            if metadata:
                cached_items.append(metadata)

        return cached_items

    def get_by_id(self, cache_id: str) -> dict[str, Any] | None:
        """Get cached item by ID."""
        metadata_file = CACHE_DIR / f'{cache_id}.json'
        return self._load_metadata(metadata_file)

    def play(self, cache_id: str) -> bool:
        """Play a cached audio file.

        Returns:
            True if played successfully.
        """
        metadata = self.get_by_id(cache_id)
        if not metadata:
            return False

        audio_path = CACHE_DIR / metadata['audio_file']
        if not audio_path.exists():
            return False

        try:
            subprocess.run(['afplay', str(audio_path)], check=True)
            return True
        except subprocess.CalledProcessError:
            return False
