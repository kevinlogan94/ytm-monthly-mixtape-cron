#!/usr/bin/env python3
"""Sync newly liked YouTube Music songs into a private monthly playlist."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from ytmusicapi import YTMusic

STATE_FILE = Path("last_synced.json")
BROWSER_AUTH_FILE = Path("browser.json")
LIKED_SONGS_LIMIT = 500


def build_playlist_title(now: datetime | None = None) -> str:
    """Return the UTC monthly playlist title, e.g. July '26 - Liked Songs."""
    if now is None:
        now = datetime.now(timezone.utc)
    month = now.strftime("%B")
    year_short = now.strftime("'%y")
    return f"{month} {year_short} - Liked Songs"


def _load_auth_raw() -> str:
    """Load auth headers from a local JSON file or the YT_AUTH_HEADERS env var."""
    local_auth_file = Path(os.environ.get("YT_AUTH_FILE", "auth.headers.json"))
    if local_auth_file.exists():
        return local_auth_file.read_text(encoding="utf-8").strip()

    headers_raw = os.environ.get("YT_AUTH_HEADERS")
    if headers_raw:
        return headers_raw.strip()

    print(
        "No auth.headers.json found and YT_AUTH_HEADERS is not set.",
        file=sys.stderr,
    )
    sys.exit(1)


def _headers_dict_to_raw(headers: dict[str, str]) -> str:
    """Normalize JSON header dict to the raw text format ytmusicapi setup expects."""
    normalized = {k.lower(): v for k, v in headers.items()}
    if not normalized.get("cookie"):
        print("YT_AUTH_HEADERS JSON is missing the Cookie header.", file=sys.stderr)
        sys.exit(1)
    normalized.setdefault("x-goog-authuser", "0")
    return "\n".join(f"{key}: {value}" for key, value in normalized.items())


def _ensure_browser_auth_file() -> None:
    """Ensure browser.json includes authorization so ytmusicapi detects browser auth."""
    headers = json.loads(BROWSER_AUTH_FILE.read_text(encoding="utf-8"))
    if headers.get("authorization") or not headers.get("cookie"):
        return
    headers["authorization"] = "SAPISIDHASH 0_init"
    BROWSER_AUTH_FILE.write_text(json.dumps(headers, indent=4, sort_keys=True), encoding="utf-8")


def init_ytmusic() -> YTMusic:
    """Initialize YTMusic from the YT_AUTH_HEADERS environment secret."""
    headers_raw = _load_auth_raw()
    try:
        parsed = json.loads(headers_raw)
    except json.JSONDecodeError:
        parsed = None

    if isinstance(parsed, dict):
        headers_raw = _headers_dict_to_raw(parsed)

    from ytmusicapi.setup import setup

    auth = setup(filepath=str(BROWSER_AUTH_FILE), headers_raw=headers_raw)
    if not auth:
        print("Failed to parse YT_AUTH_HEADERS.", file=sys.stderr)
        sys.exit(1)

    _ensure_browser_auth_file()
    return YTMusic(str(BROWSER_AUTH_FILE))


def load_state() -> dict | None:
    """Load sync state from last_synced.json, or None if missing or invalid."""
    if not STATE_FILE.exists():
        return None
    try:
        with STATE_FILE.open(encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError:
        print("last_synced.json contains invalid JSON.", file=sys.stderr)
        sys.exit(1)
    if not isinstance(data, dict):
        print("last_synced.json has an invalid format.", file=sys.stderr)
        sys.exit(1)
    last_video_id = data.get("last_video_id")
    if not last_video_id:
        return None
    return data


def save_state(last_video_id: str) -> None:
    """Persist the newest synced video ID."""
    STATE_FILE.write_text(
        json.dumps({"last_video_id": last_video_id}, indent=2) + "\n",
        encoding="utf-8",
    )


def get_or_create_monthly_playlist(yt: YTMusic, title: str) -> str:
    """Find an existing monthly playlist by exact title or create a private one."""
    playlists = yt.get_library_playlists(limit=None)
    for playlist in playlists:
        playlist_id = playlist.get("playlistId")
        if playlist.get("title") == title and playlist_id:
            return playlist_id

    return yt.create_playlist(title, "", privacy_status="PRIVATE")


def fetch_liked_tracks(yt: YTMusic) -> list[dict]:
    """Fetch liked songs, most recent first."""
    liked = yt.get_liked_songs(limit=LIKED_SONGS_LIMIT)
    return liked.get("tracks") or []


def track_video_id(track: dict) -> str | None:
    """Extract the video ID from a liked-songs track entry."""
    return track.get("videoId") or track.get("setVideoId")


def collect_new_video_ids(
    tracks: list[dict],
    anchor_id: str | None,
) -> tuple[list[str], str, str | None]:
    """
    Walk liked tracks until the anchor is found.

    Returns (new_video_ids, mode, newest_video_id) where mode is one of:
    baseline, sync, or anchor-reset.
    """
    video_ids = [vid for track in tracks if (vid := track_video_id(track))]

    if not video_ids:
        return [], "error", None

    newest_id = video_ids[0]

    if anchor_id is None:
        return [], "baseline", newest_id

    new_ids: list[str] = []
    anchor_found = False
    for video_id in video_ids:
        if video_id == anchor_id:
            anchor_found = True
            break
        new_ids.append(video_id)

    if not anchor_found:
        return [], "anchor-reset", newest_id

    return new_ids, "sync", newest_id


def add_new_songs(yt: YTMusic, playlist_id: str, video_ids: list[str]) -> int:
    """Add songs to the playlist, skipping the API call when there is nothing to add."""
    if not video_ids:
        return 0
    yt.add_playlist_items(playlist_id, video_ids, duplicates=False)
    return len(video_ids)


def write_job_summary(
    *,
    mode: str,
    playlist_title: str,
    songs_added: int,
    anchor_video_id: str | None,
    warnings: list[str] | None = None,
) -> None:
    """Append a Markdown run report to the GitHub Actions job summary."""
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY", "/dev/stdout")
    lines = [
        "## YouTube Music Liked-Songs Sync",
        "",
        f"- **Mode:** {mode}",
        f"- **Playlist:** {playlist_title}",
        f"- **Songs added:** {songs_added}",
    ]
    if anchor_video_id:
        lines.append(f"- **Anchor video ID:** `{anchor_video_id}`")
    if warnings:
        lines.extend(["", "### Warnings", ""])
        lines.extend(f"- {warning}" for warning in warnings)
    content = "\n".join(lines) + "\n"
    with open(summary_path, "a", encoding="utf-8") as f:
        f.write(content)


def main() -> None:
    yt = init_ytmusic()
    playlist_title = build_playlist_title()
    tracks = fetch_liked_tracks(yt)
    state = load_state()
    anchor_id = state.get("last_video_id") if state else None

    new_ids, mode, newest_id = collect_new_video_ids(tracks, anchor_id)

    if mode == "error":
        print("No liked songs found; cannot establish sync state.", file=sys.stderr)
        sys.exit(1)

    warnings: list[str] = []

    if mode == "baseline":
        save_state(newest_id)
        write_job_summary(
            mode="baseline",
            playlist_title=playlist_title,
            songs_added=0,
            anchor_video_id=newest_id,
        )
        return

    if mode == "anchor-reset":
        warnings.append(
            f"Stored anchor `{anchor_id}` was not found in the most recent "
            f"{LIKED_SONGS_LIMIT} liked songs. Baseline reset to `{newest_id}`; "
            "no songs were added."
        )
        save_state(newest_id)
        write_job_summary(
            mode="anchor-reset",
            playlist_title=playlist_title,
            songs_added=0,
            anchor_video_id=newest_id,
            warnings=warnings,
        )
        return

    playlist_id = get_or_create_monthly_playlist(yt, playlist_title)
    songs_added = add_new_songs(yt, playlist_id, new_ids)
    save_state(newest_id)
    write_job_summary(
        mode="sync",
        playlist_title=playlist_title,
        songs_added=songs_added,
        anchor_video_id=newest_id,
    )


if __name__ == "__main__":
    main()
