# content-tracker-adapter-podcast

Podcast RSS/Atom source adapter plugin for content-tracker.

The adapter reads a configured public RSS/Atom feed and returns metadata-only
`ContentCandidate` values. It does not download or own media files and does not access the
content-tracker database.

## Plugin registration

The package registers the `podcast` entry point in the
`content_tracker.adapters` group.

## Source configuration

Runtime feed URLs belong in the deployment-managed `sources.yaml`, not in this repository.

Example:

```yaml
apiVersion: content-tracker/v1

sources:
  - key: example-podcast
    adapter: podcast
    enabled: true
    config:
      feed_url: https://example.org/podcast/feed.xml
```

The MVP supports public HTTP(S) feeds. Private feed URLs containing credentials or tokens
should not be committed to a public repository.

## Development

The adapter relies on the host-provided `content_tracker_plugin_api`. Install the current
content-tracker backend before running the plugin tests:

```console
pip install "git+https://github.com/temeteke/content-tracker.git#subdirectory=backend"
pip install -e ".[dev]"
pytest
ruff check .
```
