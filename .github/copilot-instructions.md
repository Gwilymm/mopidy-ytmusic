# Mopidy-YTMusic: AI contributor guide

## What this project is

- Mopidy backend/frontend extension that streams from YouTube Music via `ytmusicapi` and `yt-dlp`.
- Entry point registered under `mopidy.ext` (`ytmusic`) in `pyproject.toml`; defaults come from `mopidy_ytmusic/ext.conf`.

## Architecture map

- `mopidy_ytmusic/__init__.py` defines the `Extension`, config schema, and registers backend + scrobble frontend.
- `mopidy_ytmusic/backend.py` creates the Mopidy `Backend` actor and wires providers:
  - `YTMusicPlaybackProvider` handles stream resolution via yt-dlp.
  - `YTMusicLibraryProvider` handles browse/search/lookup and caches tracks/albums/artists/images.
  - `YTMusicPlaylistsProvider` is only created when authenticated; manages playlist CRUD.
  - `YTMusicScrobbleListener` implemented by the backend so the frontend can push scrobbles back into YouTube Music.
- Timer (`RepeatingTimer`) refreshes auto-playlists on intervals from config.

## Configuration & auth workflow

- Defaults live in `ext.conf`; config schema in the extension must stay in sync.
- Guest mode works, but most features (playlists, uploads, history, like list) require `auth_json` or `oauth_json`.
- CLI helpers in `mopidy_ytmusic/command.py` (`mopidy ytmusic setup` / `reauth`) generate/refresh auth headers; `reauth` respects `oauth_json` when set.
- Keep `stream_preference` and `verify_track_url` aligned with config docs.

## Playback specifics

- `YTMusicPlaybackProvider.translate_uri` only supports `ytmusic:track:<videoId>` URIs; it sets `last_id` for “watch similar” browsing.
- Stream resolution uses **yt-dlp** to extract URLs - it handles signature decoding and player changes automatically (no manual cipher refresh needed).
- Respects `stream_preference` config (itag order); falls back to best audio-only format sorted by bitrate.
- When `verify_track_url` is enabled, a 403 head check logs an error (yt-dlp will handle retries on next extraction).
- `change_track` overrides Mopidy to always call `audio.set_metadata(track)` after `set_uri`.

## Library/browse/search patterns

- Browse roots include Artists/Albums/Subscriptions/Liked/History/“Similar to last played”/Mood & Genre/Auto playlists depending on auth and config flags.
- Auto playlists are fetched via `backend._get_auto_playlists()` using raw `ytmusicapi` browse calls and stored on `library.ytbrowse`.
- Mood/genre browsing (`ytmusic:mood`) uses `ytmusicapi` raw browse params; expect `nav(...)` helpers from `ytmusicapi.navigation`.
- `search()` supports Mopidy queries for `any`, `track_name`, `artist`/`albumartist`, `album`, or `uri` (album only) and returns `SearchResult`; `exact=True` does case-insensitive equality filtering.
- Images are cached per browseId/videoId and pulled lazily for artists/albums/playlists/tracks.

## Playlists & uploads

- Playlist provider is auth-only; CRUD uses `ytmusicapi` methods and computes add/remove deltas when saving.
- Upload content is signaled via `:upload` suffix in URIs; parsing helpers must preserve that format (see `parse_uri`).

## Scrobbling

- `mopidy_ytmusic/scrobble_fe.py` listens for `track_playback_ended`; after 50% or 120s it sends `scrobble_track` to the backend listener to update YouTube history.
- Respect the `enable_scrobbling` flag; only scrobble `ytmusic:` URIs.

## Build, tests, style

- Build: `poetry build` produces `dist/Mopidy-YTMusic-<version>.tar.gz`; install with `python3 -m pip install dist/...`.
- Tests: lightweight `unittest` cases; run `python -m pytest` or `python -m unittest discover tests` from repo root.
- Formatting: `black` (line length 80) and `isort` (profile set in `pyproject.toml`). Python support >=3.7.

## PR tips

- Keep Mopidy interfaces intact (method names/return types) or adjust tests accordingly.
- When touching playback/extraction logic, remember yt-dlp handles all signature/cipher decoding internally.
- Prefer extending existing caches (`TRACKS/ALBUMS/ARTISTS/IMAGES`) rather than creating new globals; they are used across browse/search/lookup/playback.
