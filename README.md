# OpenAR Extension Hub

Public static catalog of extensions for [OpenRA](https://github.com/HuieL/OpenRA).
OpenRA reads this repository at a pinned commit: it fetches `extensions.json`,
verifies each entry's sha256, and only then parses the entry metadata.
Browsing this catalog requires no account, and nothing here installs,
authorizes or executes anything by itself.

- Wire format: `docs/extension-hub-entry-format.md` in the OpenRA repository
  (Rust validator: `src/local/extension_hub_registry.rs`).
- Contributing: see `CONTRIBUTING.md` (metadata PRs only; developers host
  their own source and releases).
- License: repository metadata and scripts are MIT (`LICENSE`); each entry
  carries its own upstream license.

`main` holds published content only (README, index, entries, schemas,
scripts, CI, LICENSE). TODO, receipts and evidence live in the OpenRA
repository, never here.
