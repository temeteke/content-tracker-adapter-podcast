import calendar
from datetime import UTC, datetime
from time import struct_time
from urllib.parse import urlparse

import feedparser
from pydantic import AnyHttpUrl, BaseModel, ConfigDict

from content_tracker_plugin_api import (
    PLUGIN_API_VERSION,
    ContentCandidate,
    SyncContext,
    SyncResult,
)


class PodcastConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    feed_url: AnyHttpUrl


class PodcastAdapter:
    api_version = PLUGIN_API_VERSION
    config_model = PodcastConfig

    def fetch(self, context: SyncContext) -> SyncResult:
        config = PodcastConfig.model_validate(context.config.model_dump())
        parsed = feedparser.parse(str(config.feed_url))

        if getattr(parsed, "bozo", False) and not parsed.entries:
            error = getattr(parsed, "bozo_exception", "unknown feed parsing error")
            raise ValueError(f"failed to parse podcast feed: {error}")

        feed_title = str(parsed.feed.get("title", "")).strip()
        candidates: list[ContentCandidate] = []

        for entry in parsed.entries:
            candidate = _candidate_from_entry(entry, feed_title=feed_title)
            if candidate is not None:
                candidates.append(candidate)

        return SyncResult(
            candidates=candidates,
            next_state=dict(context.state),
        )


def _candidate_from_entry(entry, *, feed_title: str) -> ContentCandidate | None:
    title = str(entry.get("title", "")).strip()
    url = _entry_url(entry)
    if not title or url is None:
        return None

    metadata: dict[str, object] = {}
    if feed_title:
        metadata["feed_title"] = feed_title

    guid = entry.get("id") or entry.get("guid")
    if guid:
        metadata["guid"] = str(guid)

    return ContentCandidate(
        title=title,
        content_type="podcast",
        url=url,
        published_at=_entry_datetime(entry),
        duration_seconds=_duration_seconds(entry.get("itunes_duration")),
        metadata=metadata,
    )


def _entry_url(entry) -> str | None:
    link = _http_url(entry.get("link"))
    if link is not None:
        return link

    for enclosure in entry.get("enclosures", []):
        href = _http_url(enclosure.get("href"))
        if href is not None:
            return href

    for link_info in entry.get("links", []):
        if link_info.get("rel") != "enclosure":
            continue
        href = _http_url(link_info.get("href"))
        if href is not None:
            return href

    return None


def _http_url(value) -> str | None:
    if not value:
        return None
    text = str(value).strip()
    parsed = urlparse(text)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return text


def _entry_datetime(entry) -> datetime | None:
    value = entry.get("published_parsed") or entry.get("updated_parsed")
    if value is None:
        return None

    if isinstance(value, struct_time):
        timestamp = calendar.timegm(value)
    else:
        try:
            timestamp = calendar.timegm(tuple(value))
        except (TypeError, ValueError):
            return None

    return datetime.fromtimestamp(timestamp, tz=UTC)


def _duration_seconds(value) -> int | None:
    if value is None:
        return None

    if isinstance(value, (int, float)):
        seconds = int(value)
        return seconds if seconds >= 0 else None

    text = str(value).strip()
    if not text:
        return None

    if text.isdigit():
        return int(text)

    parts = text.split(":")
    if not 2 <= len(parts) <= 3 or not all(part.isdigit() for part in parts):
        return None

    values = [int(part) for part in parts]
    if len(values) == 2:
        minutes, seconds = values
        return minutes * 60 + seconds

    hours, minutes, seconds = values
    return hours * 3600 + minutes * 60 + seconds
