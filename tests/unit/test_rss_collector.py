"""
Unit tests for RSS Collector
"""
import pytest
from unittest.mock import patch, MagicMock
from app.services.data_collection.rss_collector import RSSCollector


class TestRSSCollector:
    def test_hash_title(self):
        collector = RSSCollector()
        h1 = collector._hash_title("Test Title")
        h2 = collector._hash_title("test title")  # Same after lowercase
        assert h1 == h2

    def test_deduplication(self):
        collector = RSSCollector()
        h = collector._hash_title("Duplicate Title")
        collector.seen_hashes.add(h)

        # Duplicate should be skipped
        with patch("feedparser.parse") as mock_parse:
            mock_entry = MagicMock()
            mock_entry.get = lambda k, d="": "Duplicate Title" if k == "title" else d
            mock_entry.published_parsed = None

            mock_feed = MagicMock()
            mock_feed.entries = [mock_entry]
            mock_feed.feed = MagicMock()
            mock_feed.feed.get = lambda k, d="": d
            mock_parse.return_value = mock_feed

            result = collector.fetch_feed("http://example.com/rss")
            assert len(result) == 0

    def test_empty_feed(self):
        collector = RSSCollector()
        with patch("feedparser.parse") as mock_parse:
            mock_feed = MagicMock()
            mock_feed.entries = []
            mock_feed.feed = MagicMock()
            mock_parse.return_value = mock_feed

            result = collector.fetch_feed("http://example.com/rss")
            assert result == []
