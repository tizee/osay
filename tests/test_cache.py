"""Tests for osay.cache module."""

import json
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch

from osay.cache import AudioCache


class TestAudioCache:
    def _make_cache(self, cache_dir: Path, **kwargs) -> AudioCache:
        with patch('osay.cache.CACHE_DIR', cache_dir):
            return AudioCache(**kwargs)

    def test_generate_cache_path_deterministic(self, tmp_path: Path):
        cache = self._make_cache(tmp_path)
        id1, path1 = cache.generate_cache_path('hello', 'onyx', 'mp3', 'cheerful')
        id2, path2 = cache.generate_cache_path('hello', 'onyx', 'mp3', 'cheerful')
        assert id1 == id2
        assert path1 == path2
        assert len(id1) == 12
        assert path1.endswith(f'{id1}.mp3')

    def test_generate_cache_path_varies_with_input(self, tmp_path: Path):
        cache = self._make_cache(tmp_path)
        id1, _ = cache.generate_cache_path('hello', 'onyx', 'mp3')
        id2, _ = cache.generate_cache_path('hello', 'coral', 'mp3')
        id3, _ = cache.generate_cache_path('world', 'onyx', 'mp3')
        assert id1 != id2
        assert id1 != id3

    def test_save_and_list_metadata(self, tmp_path: Path):
        with patch('osay.cache.CACHE_DIR', tmp_path):
            cache = self._make_cache(tmp_path)
            cache_id, cache_path = cache.generate_cache_path(
                'Hello world', 'onyx', 'mp3', 'cheerful'
            )

            # Create a fake audio file
            Path(cache_path).write_bytes(b'fake audio')

            cache.save_metadata(
                cache_id=cache_id,
                text='Hello world',
                voice='onyx',
                fmt='mp3',
                provider='OpenAITTSProvider',
                instructions='cheerful',
            )

            items = cache.list_cached()
            assert len(items) == 1
            assert items[0]['id'] == cache_id
            assert items[0]['text'] == 'Hello world'
            assert items[0]['voice'] == 'onyx'
            assert items[0]['instructions'] == 'cheerful'

    def test_lookup_hit(self, tmp_path: Path):
        with patch('osay.cache.CACHE_DIR', tmp_path):
            cache = self._make_cache(tmp_path)
            cache_id, cache_path = cache.generate_cache_path(
                'Hello world', 'onyx', 'mp3', 'cheerful'
            )
            Path(cache_path).write_bytes(b'fake audio')
            cache.save_metadata(
                cache_id=cache_id,
                text='Hello world',
                voice='onyx',
                fmt='mp3',
                provider='OpenAITTSProvider',
                instructions='cheerful',
            )

            hit = cache.lookup('Hello world', 'onyx', 'mp3', 'cheerful')
            assert hit is not None
            assert hit['id'] == cache_id
            assert hit['text'] == 'Hello world'

    def test_lookup_miss(self, tmp_path: Path):
        with patch('osay.cache.CACHE_DIR', tmp_path):
            cache = self._make_cache(tmp_path)
            assert cache.lookup('no such text', 'onyx', 'mp3') is None

    def test_lookup_miss_different_voice(self, tmp_path: Path):
        with patch('osay.cache.CACHE_DIR', tmp_path):
            cache = self._make_cache(tmp_path)
            cache_id, cache_path = cache.generate_cache_path('hello', 'onyx', 'mp3')
            Path(cache_path).write_bytes(b'audio')
            cache.save_metadata(
                cache_id=cache_id, text='hello', voice='onyx', fmt='mp3', provider='test'
            )

            # Same text, different voice -> miss
            assert cache.lookup('hello', 'coral', 'mp3') is None
            # Same text, same voice -> hit
            assert cache.lookup('hello', 'onyx', 'mp3') is not None

    def test_lookup_stale_metadata(self, tmp_path: Path):
        """Metadata exists but audio file is missing -> returns None and cleans up."""
        with patch('osay.cache.CACHE_DIR', tmp_path):
            cache = self._make_cache(tmp_path)
            cache_id, _ = cache.generate_cache_path('hello', 'onyx', 'mp3')
            # Save metadata but don't create audio file
            cache.save_metadata(
                cache_id=cache_id, text='hello', voice='onyx', fmt='mp3', provider='test'
            )

            hit = cache.lookup('hello', 'onyx', 'mp3')
            assert hit is None
            # Metadata should also be cleaned up
            assert not (tmp_path / f'{cache_id}.json').exists()

    def test_get_by_id(self, tmp_path: Path):
        with patch('osay.cache.CACHE_DIR', tmp_path):
            cache = self._make_cache(tmp_path)
            cache_id, _ = cache.generate_cache_path('test', 'coral', 'mp3')
            cache.save_metadata(
                cache_id=cache_id, text='test', voice='coral', fmt='mp3', provider='test'
            )

            result = cache.get_by_id(cache_id)
            assert result is not None
            assert result['text'] == 'test'

    def test_get_by_id_missing(self, tmp_path: Path):
        cache = self._make_cache(tmp_path)
        with patch('osay.cache.CACHE_DIR', tmp_path):
            assert cache.get_by_id('nonexistent') is None

    def test_cleanup_removes_expired(self, tmp_path: Path):
        with patch('osay.cache.CACHE_DIR', tmp_path):
            cache = self._make_cache(tmp_path, cleanup_enabled=True, cache_expire_days=7)

            # Create an expired entry (40 days old)
            old_time = (datetime.now() - timedelta(days=40)).isoformat()
            metadata = {
                'id': 'old00001',
                'timestamp': old_time,
                'text': 'old audio',
                'voice': 'onyx',
                'format': 'mp3',
                'provider': 'test',
                'instructions': None,
                'audio_file': 'old00001.mp3',
            }
            (tmp_path / 'old00001.json').write_text(json.dumps(metadata))
            (tmp_path / 'old00001.mp3').write_bytes(b'old audio data')

            # Create a fresh entry
            fresh_time = datetime.now().isoformat()
            metadata_fresh = {
                'id': 'new00001',
                'timestamp': fresh_time,
                'text': 'new audio',
                'voice': 'onyx',
                'format': 'mp3',
                'provider': 'test',
                'instructions': None,
                'audio_file': 'new00001.mp3',
            }
            (tmp_path / 'new00001.json').write_text(json.dumps(metadata_fresh))
            (tmp_path / 'new00001.mp3').write_bytes(b'new audio data')

            removed = cache.cleanup()
            assert removed == 1
            assert not (tmp_path / 'old00001.json').exists()
            assert not (tmp_path / 'old00001.mp3').exists()
            assert (tmp_path / 'new00001.json').exists()
            assert (tmp_path / 'new00001.mp3').exists()

    def test_cleanup_no_op_when_disabled(self, tmp_path: Path):
        with patch('osay.cache.CACHE_DIR', tmp_path):
            cache = self._make_cache(tmp_path, cleanup_enabled=False, cache_expire_days=7)
            cache.auto_cleanup()  # should not raise or do anything

    def test_compute_cache_key_stable(self):
        k1 = AudioCache.compute_cache_key('hello', 'onyx', 'mp3', 'cheerful')
        k2 = AudioCache.compute_cache_key('hello', 'onyx', 'mp3', 'cheerful')
        assert k1 == k2
        assert len(k1) == 12

    def test_compute_cache_key_none_instructions(self):
        k1 = AudioCache.compute_cache_key('hello', 'onyx', 'mp3', None)
        k2 = AudioCache.compute_cache_key('hello', 'onyx', 'mp3')
        assert k1 == k2
