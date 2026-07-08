# YouTube Music Monthly Liked-Songs Sync

<img src="assets/banner.png" alt="YouTube Music Monthly Mixtape banner" />

A daily GitHub Actions job that files newly liked YouTube Music tracks into a private monthly playlist (for example, `2026 July - Liked Songs`), so you get a personal mixtape each month without manual upkeep.

## How it works

1. The workflow runs once per day at midnight UTC (or on demand).
2. The script reads your liked songs, compares them to the last synced track, and adds any new likes to the current month's playlist.
3. Sync state is stored in `last_synced.json` and committed back to the repo after successful runs.
4. Each run writes a summary to the GitHub Actions Job Summary.

On the **first run**, the script records your most recent liked song as a baseline and adds nothing to a playlist — it does not backfill your entire liked library.

## Setup

### 1. Add the auth secret

Capture browser request headers from an authenticated YouTube Music session and store them as a repository secret named `YT_AUTH_HEADERS`.

1. Open [YouTube Music](https://music.youtube.com) while logged in.
2. Open browser developer tools → Network tab.
3. Filter for `/browse` requests to `music.youtube.com`.
4. Copy the request headers from an authenticated POST request (must include `Cookie`, and typically `User-Agent`, `Authorization`, `x-origin`, etc.).
5. Format them as JSON (see [ytmusicapi browser auth docs](https://ytmusicapi.readthedocs.io/en/stable/setup/browser.html)) or as raw header text.
6. In this repo: **Settings → Secrets and variables → Actions → New repository secret**
7. Name: `YT_AUTH_HEADERS`, Value: your headers JSON or raw header string.

Never commit headers or cookie credentials to the repository.

### 2. Enable workflow notifications (recommended)

In GitHub: **Settings → Notifications → Actions** — enable email alerts for failed workflows so you know when cookies need refreshing.

### 3. Run manually the first time

Go to the [Actions tab](https://github.com/kevinlogan94/ytmusic-monthly-mixtape/actions), open **Sync Liked Songs**, and click **Run workflow**. The first run establishes a baseline only.

After you like a new song, run the workflow again (or wait for the daily schedule) to see it appear in the current month's playlist.

## Viewing results

Open the [Actions tab](https://github.com/kevinlogan94/ytmusic-monthly-mixtape/actions), click a workflow run, and read the **Job summary** at the bottom of the job page. It shows the run mode (baseline, sync, or anchor reset), playlist name, songs added, and any warnings.

## Re-authentication

Browser cookie auth expires periodically. If runs start failing with auth errors, capture fresh headers from YouTube Music and update the `YT_AUTH_HEADERS` secret.

## Known limits

- **No backfill** — the first run does not populate past months with your existing liked library.
- **No unlike sync** — unliking a song does not remove it from a monthly playlist.
- **UTC month boundaries** — songs are filed into the month when the job runs, using UTC dates.
- **Inactive repo cron** — GitHub may disable scheduled workflows on repos with no activity for 60+ days. Use manual runs or keep the repo active if you rely on the schedule.

## Local development

Uses [uv](https://docs.astral.sh/uv/) for Python and dependencies (Python 3.12).

```bash
uv sync
uv run python main.py
```

For local auth, put captured headers in `auth.headers.json` (gitignored):

```json
{
  "Cookie": "...",
  "User-Agent": "...",
  "x-origin": "https://music.youtube.com",
  "x-goog-authuser": "0"
}
```

GitHub Actions uses the `YT_AUTH_HEADERS` secret instead. You can also `export YT_AUTH_HEADERS='...'` — avoid putting JSON in `.env` with `uv run --env-file`; dotenv parsers strip quotes from cookie values.

If `x-goog-authuser` is missing locally, the script defaults it to `0`.

`browser.json` is created locally for auth and is gitignored. Do not commit it or `.env`.
