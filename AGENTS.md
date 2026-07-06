# AGENTS.md

Instructions for AI agents working in this repo.

## Before you write code

1. Read the architecture document and epic breakdown.
2. If they disagree, follow the architecture document.
3. If you change a locked decision, update both documents.

Architecture document: `docs/architecture.md`

Epic breakdown: `_bmad-output/planning-artifacts/epics.md`

## How to work

- Keep the implementation and approach simple.
- When planning a body of work, focus on how to accomplish it in the least amount of code possible.
- Keep changes small and focused.
- Match patterns already in the codebase.
- Do not add v1 scope unless the user asks for it.
- Do not guess on security or architecture — read the docs or ask.

## Secrets

Never put YouTube Music auth headers or cookie credentials in committed files or in env vars outside GitHub Actions secrets.

## Ops notes

For cookie re-auth, failed sync runs, and other human tasks, see `README.md`.
