# Story 1.1: Build the Complete Monthly Liked-Songs Sync Pipeline

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a YouTube Music listener,
I want my newly liked songs automatically filed into a private monthly playlist,
so that I have a personal mixtape for each month without manual upkeep.

## Acceptance Criteria

1. **Greenfield deliverables** — Repo contains `main.py`, `requirements.txt`, `.github/workflows/sync.yml`, and `README.md`. `last_synced.json` is **not** in the initial commit (created at runtime only).

2. **GitHub Actions workflow** — `.github/workflows/sync.yml`:
   - Schedule: `cron: '0 0 * * *'` (midnight UTC daily)
   - `workflow_dispatch` for manual runs
   - `runs-on: ubuntu-latest`, Python **3.12**
   - Installs from `requirements.txt`, runs `main.py`
   - `permissions: contents: write`
   - Reads auth from repository secret `YT_AUTH_HEADERS`
   - On success, commits **only** `last_synced.json` with a clear automated commit message
   - On failure, exits non-zero; no partial/corrupt `last_synced.json` committed

3. **Auth & playlist title** — `main.py` with valid `YT_AUTH_HEADERS`:
   - Initializes ytmusicapi from browser-cookie headers (FR1, NFR6)
   - Derives current-month playlist title in UTC: `{Month} '{YY} - Liked Songs` (e.g. `July '26 - Liked Songs`) (FR3)

4. **Find or create monthly playlist** (FR4):
   - If title absent → `create_playlist(..., privacy_status='PRIVATE')`
   - If title exists → reuse; never create duplicate

5. **First run (no `last_synced.json`)** (FR6, FR9):
   - `get_liked_songs()` most-recent-first
   - Write `{"last_video_id": "<newest>"}` 
   - Add **zero** songs to any playlist
   - Job summary states baseline established (FR10)

6. **Normal sync (anchor found, new likes exist)** (FR2, FR7, FR8, FR9):
   - Walk liked songs top-down until stored `last_video_id` reached
   - Add songs above anchor to current month's playlist via `add_playlist_items()`
   - Update `last_synced.json` to newest video ID
   - Job summary: playlist name, songs added count, outcome (FR10)

7. **Missing anchor** (FR13):
   - If stored `last_video_id` not in fetched liked-songs list → reset baseline to current newest ID, add no songs, warn clearly in summary (FR10)

8. **Idempotency** (FR5, NFR3):
   - Two consecutive runs with no new likes → no duplicate playlist entries; `last_video_id` unchanged

9. **README** (NFR5, NFR9):
   - Plain language: what/why, header capture → `YT_AUTH_HEADERS`, manual run, Actions tab Job Summary, re-auth on failure
   - Known limits: no backfill, no unlike sync, UTC month boundaries, inactive-repo cron caveat

10. **Scope guardrails** — No database, dashboard, OAuth flow, tests, or removal-sync logic (NFR1, NFR2).

## Tasks / Subtasks

- [ ] **Task 1: Project scaffold** (AC: 1, 10)
  - [ ] Create `requirements.txt` with `ytmusicapi` (pin `>=1.12.1,<2`)
  - [ ] Create `.gitignore` entry for local `browser.json` if used during dev (optional but recommended)
  - [ ] Do **not** add `last_synced.json` to repo

- [ ] **Task 2: Implement `main.py` sync logic** (AC: 3–8)
  - [ ] Load `YT_AUTH_HEADERS` env var → initialize `YTMusic`
  - [ ] `build_playlist_title()` using UTC `datetime`
  - [ ] `load_state()` / `save_state()` for `last_synced.json`
  - [ ] `get_or_create_monthly_playlist(title)` via `get_library_playlists(limit=None)`
  - [ ] `fetch_liked_tracks()` via `get_liked_songs(limit=...)`
  - [ ] `collect_new_video_ids(tracks, anchor_id | None)` — walk until anchor; handle first-run & missing-anchor
  - [ ] `add_new_songs(playlist_id, video_ids)` — batch `add_playlist_items(..., duplicates=False)`
  - [ ] `write_job_summary(...)` → append Markdown to `$GITHUB_STEP_SUMMARY`
  - [ ] Top-level `main()` with fail-fast: any API/state error → `sys.exit(1)` before commit step can run

- [ ] **Task 3: GitHub Actions workflow** (AC: 2, 11)
  - [ ] `.github/workflows/sync.yml` with schedule + dispatch
  - [ ] `actions/checkout@v4` with `token` for push
  - [ ] `actions/setup-python@v5` with `python-version: '3.12'`
  - [ ] Run `main.py` with `YT_AUTH_HEADERS: ${{ secrets.YT_AUTH_HEADERS }}`
  - [ ] Conditional commit step: only if `last_synced.json` changed; `git add last_synced.json` only

- [ ] **Task 4: README** (AC: 9)
  - [ ] Short, human-readable setup and ops guide
  - [ ] Link to repo Actions tab for Job Summary

## Dev Notes

### Epic context

Single epic, single story — delivers the entire v1 pipeline. All FR1–FR13 and NFR1–NFR9 apply to this story. No prior stories; greenfield repo (only BMAD planning docs and `docs/architecture.md` exist today).

### Authoritative spec vs architecture doc

**Follow epics + frontmatter clarifications when they differ from `docs/architecture.md`:**

| Topic | Epics (authoritative) | Architecture (stale) |
|-------|----------------------|----------------------|
| Cron | `0 0 * * *` midnight UTC | `0 13 * * *` (~9am ET) |
| Playlist title | `July '26 - Liked Songs` | `Liked - July 2026` |
| Initial `last_synced.json` | Not committed | Listed in repo structure |

[Source: _bmad-output/planning-artifacts/epics.md#clarifications]

### End-to-end run sequence

```
1. Read YT_AUTH_HEADERS → YTMusic(headers)
2. title = UTC month title
3. playlist_id = find by exact title OR create_playlist(title, "", privacy_status="PRIVATE")
4. liked = get_liked_songs(limit=N)  → tracks in liked["tracks"]
5. state = load last_synced.json or None
6. Branch:
   - No state → baseline newest videoId, save, summary "baseline", exit 0
   - Anchor missing in tracks → reset baseline, warn, exit 0
   - Else → new_ids = tracks above anchor → add_playlist_items → save newest → summary
7. Workflow commits last_synced.json if changed
```

### Project Structure Notes

Target layout (v1):

```
/
├── .github/workflows/sync.yml
├── main.py
├── requirements.txt
├── README.md
└── last_synced.json          # runtime only, committed by workflow after runs
```

Keep everything in one `main.py` — no package subdirs, no tests dir (explicitly out of scope).

### Architecture compliance

- **NFR1/NFR2:** Single script + thin workflow; flat JSON state file only
- **NFR3:** Idempotent via anchor walk + `add_playlist_items(..., duplicates=False)` (ytmusicapi default skips dupes)
- **NFR4:** Midnight UTC cron
- **NFR6:** Browser headers secret, not OAuth
- **NFR7:** Uncaught exceptions / explicit `sys.exit(1)` on failure
- **NFR8:** Python 3.12 on ubuntu-latest
- **Month bucketing:** UTC system date; songs filed in month job runs, not historical like date
- **First run:** Baseline only — never backfill entire liked library

[Source: docs/architecture.md §2–7, epics.md Requirements Inventory]

### Technical requirements

**Auth initialization**

- Store raw browser request headers as JSON in `YT_AUTH_HEADERS` (must include `Cookie` and typically `User-Agent`, `x-origin`, etc.)
- In CI: `headers_json = os.environ["YT_AUTH_HEADERS"]` → write temp file OR pass to `YTMusic()` per ytmusicapi browser auth pattern
- Recommended pattern: write to ephemeral `browser.json` in workflow temp dir, `YTMusic("browser.json")`, never commit that file
- Alternative: `from ytmusicapi.setup import setup; auth = setup(headers_raw=raw_headers); yt = YTMusic(auth)`

[Source: ytmusicapi browser auth docs v1.12.1]

**Playlist title format**

```python
# UTC example for 2026-07-06 → "July '26 - Liked Songs"
month = now.strftime("%B")           # July
year_short = now.strftime("'%y")     # '26
title = f"{month} {year_short} - Liked Songs"
```

**State file**

```json
{ "last_video_id": "dQw4w9WgXcQ" }
```

- Read/write `./last_synced.json` relative to repo root (workflow cwd)
- Only write after successful API operations
- On script crash, leave file unchanged so workflow commit step skips or commits last good state

**Liked songs fetch — pagination guardrail**

- `get_liked_songs(limit=100)` default caps at 100 tracks
- **Must use a high limit** (e.g. `500`) or paginate until anchor found / list exhausted
- If anchor not found within fetched window → treat as FR13 missing-anchor reset (do not silently miss songs)
- Extract `videoId` from each track in `liked["tracks"]` (dict shape matches `get_playlist()`)

**Library playlist lookup**

- `get_library_playlists(limit=None)` — default limit is 25; monthly playlist may be missed if user has >25 playlists
- Match on **exact** `title` string equality

**Adding songs**

- `add_playlist_items(playlistId, videoIds, duplicates=False)` — pass list oldest-first or newest-first; order in playlist is low priority for v1
- Empty `video_ids` → skip API call

**Job summary**

- Append to `os.environ.get("GITHUB_STEP_SUMMARY", "/dev/stdout")` for local dev fallback
- Include: run mode (baseline / sync / anchor-reset), playlist title, songs added count, anchor video ID, warnings

**Workflow commit pattern**

```yaml
permissions:
  contents: write
# ...
- uses: actions/checkout@v4
  with:
    token: ${{ secrets.GITHUB_TOKEN }}
- name: Commit sync state
  run: |
    git config user.name "github-actions[bot]"
    git config user.email "github-actions[bot]@users.noreply.github.com"
    git add last_synced.json
    git diff --staged --quiet || git commit -m "chore: update liked-songs sync state"
    git push
```

Only run commit step after successful `main.py` exit 0. Do not commit if script failed.

### Library & framework requirements

| Dependency | Version | Notes |
|------------|---------|-------|
| Python | 3.12 | GitHub Actions + local dev |
| ytmusicapi | >=1.12.1,<2 | Latest stable 1.12.1 (Jun 2026); requires Python >=3.10 |
| stdlib only otherwise | — | `json`, `os`, `sys`, `datetime`, `pathlib` |

`requirements.txt` example: `ytmusicapi>=1.12.1,<2`

Key API methods:
- `YTMusic(auth)` — browser JSON file or setup string
- `get_liked_songs(limit)` → `{"tracks": [...]}`
- `get_library_playlists(limit=None)` → `[{"playlistId", "title", ...}]`
- `create_playlist(title, description, privacy_status="PRIVATE")` → playlistId
- `add_playlist_items(playlistId, videoIds, duplicates=False)`

[Source: ytmusicapi.readthedocs.io v1.12.1]

### File structure requirements

| File | Action | Purpose |
|------|--------|---------|
| `main.py` | NEW | All sync logic |
| `requirements.txt` | NEW | ytmusicapi pin |
| `.github/workflows/sync.yml` | NEW | Cron + manual + commit |
| `README.md` | NEW | Setup/ops docs |
| `last_synced.json` | RUNTIME | Created by script; committed by workflow |

Do **not** create: tests, `src/` package, Dockerfile, OAuth helpers, web UI.

### Testing requirements

**None for v1** — explicit out of scope per epics. Manual verification:
1. First manual `workflow_dispatch` with valid headers → baseline summary, no playlist adds
2. Like a song, re-run → song appears in current month playlist
3. Re-run immediately → 0 adds, idempotent

### Latest tech information

- **ytmusicapi 1.12.1** (2026-06-05): Active maintenance; browser-cookie auth remains supported alongside OAuth
- **Browser auth tradeoff:** Cookies expire periodically; README must document re-capture. Failures surface via GitHub email (NFR7)
- **`add_playlist_items` duplicates param:** Default `False` — aligns with FR5 idempotency
- **GitHub Actions cron caveat:** Scheduled workflows only run on default branch; repos inactive 60+ days may stop cron — document in README

### Project context reference

No `project-context.md` found in repo. Primary sources:
- `_bmad-output/planning-artifacts/epics.md` — requirements & BDD acceptance criteria
- `docs/architecture.md` — architecture patterns (defer to epics where conflicting)

### Anti-patterns to avoid

- Do not use OAuth setup — out of scope; headers secret only
- Do not commit `browser.json` or raw headers
- Do not backfill on first run
- Do not remove songs from playlists on unlike
- Do not add unit/integration test suite
- Do not use architecture doc cron/title formats
- Do not call `get_library_playlists()` without `limit=None`
- Do not rely on default `get_liked_songs()` limit of 100 for anchor walks

### References

- [Source: _bmad-output/planning-artifacts/epics.md — Story 1.1, FR/NFR inventory]
- [Source: docs/architecture.md — §3–8 data flow, components, trade-offs]
- [Source: https://ytmusicapi.readthedocs.io/en/stable/setup/browser.html — browser auth]
- [Source: https://ytmusicapi.readthedocs.io/en/stable/reference/playlists.html — create/add playlist]
- [Source: https://ytmusicapi.readthedocs.io/en/stable/reference/api/ytmusicapi.mixins.html — get_liked_songs, get_library_playlists]

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created

### File List
