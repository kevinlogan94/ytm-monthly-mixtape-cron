# Deferred Work

- source_spec: `_bmad-output/implementation-artifacts/1-1-build-the-complete-monthly-liked-songs-sync-pipeline.md`
  summary: Update docs/architecture.md to match epics (cron, playlist title format, runtime-only last_synced.json).
  evidence: AGENTS.md requires architecture alignment when locked decisions change; architecture.md still documents stale cron/title/state conventions.

- source_spec: `_bmad-output/implementation-artifacts/1-1-build-the-complete-monthly-liked-songs-sync-pipeline.md`
  summary: Paginate liked-songs fetch beyond 500 tracks when anchor not found in first window.
  evidence: Users with >500 likes and long gaps between runs may hit false anchor-reset; spec allows pagination as alternative guardrail but v1 uses fixed high limit only.
