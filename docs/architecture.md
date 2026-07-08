# YouTube Music Monthly Liked-Songs Playlist — Architecture Document

## 1. Overview
A daily automated job that scans the user's YouTube Music liked songs and files newly-liked
tracks into a playlist named for the current month (e.g. "2026 July - Liked Songs"), replacing
reliance on YouTube's algorithmic seasonal playlists.

## 2. Goals & Constraints
- Minimal code footprint (v1)
- No database / backend service to manage
- No duplicate work needed - approach must be idempotent
- Runs once daily
- Includes a lightweight way to observe job activity (reporting)

## 3. High-Level Architecture

```
GitHub Actions (cron trigger, daily)
        |
        v
Python script (main.py)
        |
        +--> ytmusicapi: get_liked_songs()   [most-recent-first]
        +--> ytmusicapi: get_library_playlists() / create_playlist()
        +--> ytmusicapi: add_playlist_items()
        |
        +--> reads/writes last_synced.json (committed to repo)
        |
        v
GitHub Actions Job Summary (reporting output)
```

No external servers, databases, or cloud accounts required beyond GitHub itself.

## 4. Components

### 4.1 Scheduler: GitHub Actions cron
- Workflow file: `.github/workflows/sync.yml`
- Trigger: `schedule: cron: '0 13 * * *'` (runs daily, ~9am ET)
- Runs on `ubuntu-latest`, sets up Python, installs `ytmusicapi`, runs `main.py`
- Note: cron only fires on the default branch; inactive repos (60+ days) may stop firing

### 4.2 Core logic: main.py (Python + ytmusicapi)
Sequence per run:
1. Determine current month name from system date -> playlist title (e.g. "2026 July - Liked Songs")
2. Call `get_library_playlists()`; if the month's playlist doesn't exist, `create_playlist()`
3. Call `get_liked_songs()` (ordered most-recent-first)
4. Read `last_synced.json` for the last-known most-recent video ID
5. Walk down the liked-songs list until that ID is reached -> these are the new songs
6. `add_playlist_items()` to add new songs to the current month's playlist
7. Overwrite `last_synced.json` with the newest video ID
8. Write a Markdown report to `$GITHUB_STEP_SUMMARY`
9. Commit the updated `last_synced.json` back to the repo

### 4.3 State: last_synced.json (flat file, not a database)
```json
{ "last_video_id": "dQw4w9WgXcQ" }
```
- Single field, committed to the repo by the workflow after each run
- Replaces need for a database table
- First-run behavior: no file exists yet -> script records current most-recent liked ID,
  adds nothing to a playlist (avoids dumping entire liked-songs backlog into one month)

### 4.4 Auth: ytmusicapi browser-cookie headers
- Captured once from an authenticated browser session, stored as a GitHub Actions secret
  (e.g. `YT_AUTH_HEADERS`)
- Avoids Google Cloud OAuth "Testing mode" 7-day refresh token expiry trap
- Tradeoff: cookies can occasionally invalidate and require a manual re-capture

### 4.5 Reporting: GitHub Actions Job Summary
- Script writes Markdown to `$GITHUB_STEP_SUMMARY` each run (songs added, playlist name, counts)
- Rendered automatically on the workflow run page in the GitHub Actions tab
- No separate hosting, dashboard, or database needed
- README links directly to the repo's Actions tab for quick access

### 4.6 Failure visibility
- GitHub's built-in "notify me on failed workflows" email setting enabled
- Zero additional code required

## 5. Data Flow Summary

| Step | Source | Destination |
|------|--------|-------------|
| Read liked songs | YouTube Music (via ytmusicapi) | Script memory |
| Determine new songs | last_synced.json + liked songs list | Script memory |
| Create/find monthly playlist | YouTube Music | YouTube Music |
| Add new songs | Script memory | YouTube Music playlist |
| Update state | Script memory | last_synced.json (committed to repo) |
| Report | Script memory | GitHub Actions Job Summary |

## 6. Known Trade-offs / Edge Cases

| Issue | Handling |
|-------|----------|
| No "date liked" timestamp from API | Month bucket = month the job processes the like, not historical like date |
| First run backlog | Baseline snapshot approach - no backlog dump into current month |
| Timezone edge cases at month boundary | Accepted as-is (UTC-based); rare edge case, not worth extra logic |
| Unliking a song after it's filed | Not handled in v1 (add-only, no removal sync) |
| Cookie auth expiry | Manual re-capture when needed; flagged via failure email notification |
| Repo inactivity disabling cron | Documented in README as a known GitHub Actions limitation |

## 7. Explicitly Out of Scope (v1)
- Database or persistent backend service
- Web dashboard / Nuxt interface
- OAuth-based auth flow
- Historical backfill of pre-existing liked songs into past monthly playlists
- Removal sync (unliking a song does not remove it from its monthly playlist)

## 8. Repository Structure

```
/
├── .github/
│   └── workflows/
│       └── sync.yml
├── main.py
├── pyproject.toml
├── uv.lock
├── last_synced.json
└── README.md
```

## 9. README Requirements
- Plain-language explanation of what the job does and why
- Setup steps for capturing and storing the YT_AUTH_HEADERS secret
- Link/instructions to view the latest run's Job Summary in the Actions tab
- Note on manual re-auth if the job starts failing
