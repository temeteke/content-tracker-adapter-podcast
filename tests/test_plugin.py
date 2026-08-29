from importlib.metadata import entry_points
from time import struct_time

import feedparser
import pytest
from pydantic import ValidationError

from content_tracker_adapter_podcast.plugin import PodcastAdapter, PodcastConfig
from content_tracker_plugin_api import SyncContext


def test_package_registers_podcast_entry_point():
    adapters = {
        entry_point.name: entry_point
        for entry_point in entry_points(group="content_tracker.adapters")
    }

    assert "podcast" in adapters


def test_config_requires_http_url():
    with pytest.raises(ValidationError):
        PodcastConfig(feed_url="not-a-url")


def test_fetch_maps_feed_entries(monkeypatch):
    parsed = feedparser.FeedParserDict(
        {
            "feed": {"title": "Example Podcast"},
            "entries": [
                feedparser.FeedParserDict(
                    {
                        "title": "Episode 1",
                        "link": "https://example.org/episodes/1",
                        "id": "episode-1",
                        "published_parsed": struct_time(
                            (2026, 8, 29, 12, 0, 0, 5, 241, 0)
                        ),
                        "itunes_duration": "01:02:03",
                    }
                )
            ],
            "bozo": False,
        }
    )
    monkeypatch.setattr(feedparser, "parse", lambda url: parsed)

    config = PodcastConfig(feed_url="https://example.org/feed.xml")
    result = PodcastAdapter().fetch(
        SyncContext(source_key="example", config=config)
    )

    assert len(result.candidates) == 1
    candidate = result.candidates[0]
    assert candidate.title == "Episode 1"
    assert candidate.content_type == "podcast"
    assert candidate.url == "https://example.org/episodes/1"
    assert candidate.duration_seconds == 3723
    assert candidate.metadata == {
        "feed_title": "Example Podcast",
        "guid": "episode-1",
    }
    assert candidate.published_at is not None


def test_fetch_uses_enclosure_when_entry_has_no_page_link(monkeypatch):
    parsed = feedparser.FeedParserDict(
        {
            "feed": {},
            "entries": [
                feedparser.FeedParserDict(
                    {
                        "title": "Episode",
                        "links": [
                            {
                                "rel": "enclosure",
                                "href": "https://media.example.org/episode.mp3",
                            }
                        ],
                    }
                )
            ],
            "bozo": False,
        }
    )
    monkeypatch.setattr(feedparser, "parse", lambda url: parsed)

    config = PodcastConfig(feed_url="https://example.org/feed.xml")
    result = PodcastAdapter().fetch(
        SyncContext(source_key="example", config=config)
    )

    assert result.candidates[0].url == "https://media.example.org/episode.mp3"


def test_fetch_rejects_unparseable_feed(monkeypatch):
    parsed = feedparser.FeedParserDict(
        {
            "feed": {},
            "entries": [],
            "bozo": True,
            "bozo_exception": ValueError("bad feed"),
        }
    )
    monkeypatch.setattr(feedparser, "parse", lambda url: parsed)

    config = PodcastConfig(feed_url="https://example.org/feed.xml")
    with pytest.raises(ValueError, match="failed to parse"):
        PodcastAdapter().fetch(
            SyncContext(source_key="example", config=config)
        )
