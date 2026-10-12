# Contributing to the OpenAR Extension Hub

This repository is a static catalog. OpenRA reads `extensions.json` at a pinned
commit SHA and verifies each entry's sha256 before use. There is no server, no
account, and no install script to run here.

## Adding an entry

1. Host your extension in your own repository. This hub does not copy
   third-party repositories; `delivery` decides what an install resolves to:
   - `bundled` — ships with the OpenRA app; listed read-only, no assets;
   - `package` / `cli` — a pinned release artifact per platform;
   - `mcp-local` — a package whose MCP server command runs inside the
     installed tree;
   - `mcp-remote` — a registered connection; nothing is downloaded.
2. Create `entries/extensions/<id>/entry.json` following
   `schemas/extension-entry.schema.json`. The required facts:
   - `id` — lowercase namespaced identity (e.g. `openra.calendar`), equal to
     the directory name, globally unique, never reused;
   - `source` — public HTTPS repo URL, the extension's subdirectory, and an
     exact 40-hex commit SHA. `main`/`latest`/mutable tags are never accepted
     as a pin;
   - `assets` — for installable deliveries, one pinned HTTPS artifact per
     platform with sha256 and size;
   - `license` — SPDX id; the entry must state the license its content
     actually carries.
3. Run `python3 scripts/build-index.py` and commit the regenerated
   `extensions.json` together with your entry.
4. Open a PR. CI runs `scripts/validate.py` (read-only, no secrets, no
   install step; it never executes anything from your entry).

## What review means

`review.status` records what a human looked at, and `reviewedRevision` pins
which revision that covered. `unreviewed` is not an accusation and `reviewed`
is not a guarantee; neither grants anything on a user's machine. Declarations
in an entry (capabilities, uiContributions, bindings) are claims the host
verifies at install and use time — declared is not detected, detected is not
verified.

## Updates and removal

A new upstream revision is a new `source.revision` plus a new `assets`/`mcp`
manifest; the index is regenerated in the same PR. Deprecated or high-risk
entries keep their history — upstream deletion never silently removes a
catalog record.
