---
stepsCompleted:
  - step-01-validate-prerequisites
  - step-02-design-epics
inputDocuments:
  - docs/architecture.md
clarifications:
  requirements_source: docs/architecture.md (no PRD)
  epic_structure: 1 epic, 1 story
  schedule: "0 0 * * * (midnight UTC daily)"
  playlist_title_format: "2026 July - Liked Songs"
  playlist_visibility: private
  first_run: baseline only, no backlog dump
  missing_sync_anchor: reset baseline, warn in summary, no adds
  initial_last_synced_json: not committed to repo
  tests: none
  readme_style: short, human-readable, plain language
  python_version: "3.12"
---

# ytm-monthly-mixtape-cron - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for ytm-monthly-mixtape-cron, decomposing requirements from the Architecture document into implementable stories.

## Requirements Inventory

### Functional Requirements

FR1: A daily automated job scans the user's YouTube Music liked songs via ytmusicapi.
FR2: Newly liked songs since the last run are added to a playlist named for the current month.
FR3: Monthly playlist titles follow the format `{YYYY} {Month} - Liked Songs` (e.g. `2026 July - Liked Songs`).
FR4: The job finds an existing monthly playlist by title or creates a new private playlist if one does not exist.
FR5: Sync is idempotent — re-running the job on the same day adds no duplicate songs.
FR6: On first run (no `last_synced.json`), the job records the current most-recent liked-song video ID as baseline and adds nothing to any playlist.
FR7: On subsequent runs, the job walks the liked-songs list (most-recent-first) until it reaches the stored `last_video_id`; songs above that anchor are new.
FR8: New songs are added to the current month's playlist via `add_playlist_items()`.
FR9: After a successful run, `last_synced.json` is overwritten with the newest liked-song video ID.
FR10: Each run writes a Markdown report to `$GITHUB_STEP_SUMMARY` (songs added, playlist name, counts, baseline/reset notices).
FR11: The GitHub Actions workflow commits the updated `last_synced.json` back to the repo after each run.
FR12: The workflow supports `workflow_dispatch` for manual runs during setup and debugging.
FR13: If the stored `last_video_id` is not found in the current liked-songs list, the job resets the baseline to the current newest ID, logs a warning in the job summary, and adds no songs.

### NonFunctional Requirements

NFR1: Minimal code footprint — v1 should be a single Python script plus thin workflow wrapper.
NFR2: No database or persistent backend service; state lives in a flat `last_synced.json` file.
NFR3: The sync approach must be idempotent with no duplicate work across runs.
NFR4: The job runs once daily on a cron schedule of `0 0 * * *` (midnight UTC).
NFR5: Job activity is observable via GitHub Actions Job Summary — no separate dashboard or hosting.
NFR6: Authentication uses browser-cookie headers stored as a GitHub Actions secret (`YT_AUTH_HEADERS`).
NFR7: Workflow failures are surfaced via GitHub's built-in failed-workflow email notifications (no custom alerting code).
NFR8: Python 3.12 on `ubuntu-latest` in GitHub Actions.
NFR9: README is short, plain-language, and human-readable — not a technical manual.

### Additional Requirements

- Repository structure: `.github/workflows/sync.yml`, `main.py`, `requirements.txt`, `README.md`; `last_synced.json` created at runtime, not in initial repo.
- Workflow installs `ytmusicapi` from `requirements.txt` and runs `main.py`.
- Workflow grants `permissions: contents: write` for committing `last_synced.json`.
- Commit step touches only `last_synced.json` to avoid noisy repo commits.
- Auth setup documented in README: capture browser headers once, store as `YT_AUTH_HEADERS` secret, note manual re-capture on cookie expiry.
- README links to the repo Actions tab for viewing Job Summary output.
- README documents known limitations: no historical backfill, no unlike/removal sync, UTC month boundaries, inactive-repo cron caveat.
- Month bucketing uses UTC system date; timezone edge cases at month boundary are accepted without extra logic.
- Songs are filed by the month the job processes them, not by a historical "date liked" (API does not provide this).
- Explicitly out of scope for v1: database, web dashboard, OAuth auth flow, historical backfill, removal sync, unit/integration tests.

### UX Design Requirements

Not applicable — v1 has no user interface. Observability is via GitHub Actions Job Summary and README.

### FR Coverage Map

FR1: Epic 1 — Daily scan of liked songs via ytmusicapi
FR2: Epic 1 — Add new likes to current month's playlist
FR3: Epic 1 — Playlist title format `{YYYY} {Month} - Liked Songs`
FR4: Epic 1 — Find or create private monthly playlist
FR5: Epic 1 — Idempotent sync (no duplicates on re-run)
FR6: Epic 1 — First-run baseline snapshot, no backlog dump
FR7: Epic 1 — Walk liked-songs list until sync anchor
FR8: Epic 1 — Add new songs via add_playlist_items()
FR9: Epic 1 — Persist last_video_id to last_synced.json
FR10: Epic 1 — Markdown report to GITHUB_STEP_SUMMARY
FR11: Epic 1 — Workflow commits last_synced.json to repo
FR12: Epic 1 — workflow_dispatch for manual runs
FR13: Epic 1 — Missing anchor resets baseline with warning

## Epic List

### Epic 1: Monthly Liked-Songs Mixtape

YouTube Music listeners get newly liked songs filed into a private monthly playlist automatically, without manual playlist upkeep or relying on YouTube's seasonal mixes.

**FRs covered:** FR1, FR2, FR3, FR4, FR5, FR6, FR7, FR8, FR9, FR10, FR11, FR12, FR13

## Epic 1: Monthly Liked-Songs Mixtape

YouTube Music listeners get newly liked songs filed into a private monthly playlist automatically, without manual playlist upkeep or relying on YouTube's seasonal mixes.

### Story 1.1: Build the Complete Monthly Liked-Songs Sync Pipeline

As a YouTube Music listener,
I want my newly liked songs automatically filed into a private monthly playlist,
So that I have a personal mixtape for each month without manual upkeep.

**Acceptance Criteria:**

**Given** a greenfield repository with no application code yet
**When** the story is complete
**Then** the repo contains `main.py`, `requirements.txt`, `.github/workflows/sync.yml`, and `README.md`
**And** `last_synced.json` is not included in the initial commit (created at runtime)

**Given** the GitHub Actions workflow is configured
**When** inspecting `.github/workflows/sync.yml`
**Then** it runs on `schedule: cron: '0 0 * * *'` (midnight UTC daily)
**And** it supports `workflow_dispatch` for manual runs
**And** it uses `ubuntu-latest` with Python 3.12
**And** it installs dependencies from `requirements.txt` and runs `main.py`
**And** it sets `permissions: contents: write`
**And** it reads auth headers from the `YT_AUTH_HEADERS` repository secret

**Given** `main.py` runs with valid `YT_AUTH_HEADERS`
**When** the script executes
**Then** it initializes ytmusicapi using the provided browser-cookie headers (FR1, NFR6)
**And** it derives the current month's playlist title in the format `{YYYY} {Month} - Liked Songs` using UTC (e.g. `2026 July - Liked Songs`) (FR3)

**Given** the monthly playlist does not yet exist in the user's library
**When** the script runs
**Then** it creates a new private playlist with the derived title (FR4)
**And** if the playlist already exists, it reuses it without creating a duplicate (FR4)

**Given** no `last_synced.json` file exists (first run)
**When** the script runs
**Then** it fetches liked songs (most-recent-first) via `get_liked_songs()` (FR1)
**And** it writes `last_synced.json` with the newest liked-song video ID (FR6, FR9)
**And** it adds zero songs to any playlist (FR6)
**And** the job summary states that a baseline was established (FR10)

**Given** `last_synced.json` exists with a valid `last_video_id` still present in the liked-songs list
**When** the script runs and there are new likes since the last run
**Then** it collects all liked songs above the anchor ID (most-recent-first walk) (FR7)
**And** it adds those songs to the current month's playlist via `add_playlist_items()` (FR2, FR8)
**And** it updates `last_synced.json` with the new newest video ID (FR9)
**And** the job summary reports playlist name, count of songs added, and run outcome (FR10)

**Given** `last_synced.json` exists but the stored `last_video_id` is not found in the current liked-songs list
**When** the script runs
**Then** it resets the baseline to the current newest liked-song video ID (FR13)
**And** it adds no songs to any playlist (FR13)
**And** the job summary includes a clear warning about the anchor reset (FR10, FR13)

**Given** the script runs twice in succession with no new likes between runs
**When** the second run completes
**Then** no duplicate songs are added to the playlist (FR5, NFR3)
**And** `last_synced.json` reflects the same newest video ID (FR5)

**Given** a successful run that created or updated `last_synced.json`
**When** the workflow finishes
**Then** it commits only `last_synced.json` back to the default branch (FR11)
**And** the commit message clearly identifies it as an automated sync state update

**Given** a workflow run fails (e.g. expired cookies, API error)
**When** the failure occurs
**Then** the workflow exits with a non-zero status so GitHub's failed-workflow email notification fires (NFR7)
**And** no partial or corrupt `last_synced.json` is committed

**Given** a new user reads `README.md`
**When** they follow the setup instructions
**Then** they understand in plain language what the job does and why it exists (NFR9)
**And** they can capture browser auth headers and store them as the `YT_AUTH_HEADERS` secret
**And** they know how to trigger a manual run and find the Job Summary on the Actions tab (NFR5)
**And** they know to re-capture headers if the job starts failing
**And** known limitations are stated simply: no backfill, no unlike sync, UTC month boundaries, inactive-repo cron caveat

**Given** the v1 scope defined in the architecture document
**When** reviewing the delivered code
**Then** there is no database, web dashboard, OAuth flow, test suite, or removal-sync logic (out of scope)
**And** the implementation remains a single Python script plus a thin workflow wrapper (NFR1, NFR2)
