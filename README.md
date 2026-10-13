# OpenAR Extension Hub

Public static catalog of extensions for OpenAR.
OpenAR reads this repository at a pinned commit: it fetches `extensions.json`,
verifies each entry's sha256, and only then parses the entry metadata.
Browsing this catalog requires no account, and nothing here installs,
authorizes or executes anything by itself.

- Wire format: `docs/extension-hub-entry-format.md` in the OpenAR repository.
- Public contract: `docs/public-contract.md` in the OpenAR repository,
  pinned at commit `ff5848c5e108ac8675be94457a7dafb4abb4c804`. It defines
  the publishable boundary and field meanings; this repository's schema and
  validators are the kind-specific checkers, and a reference is not host
  authorization.
- Contributing: see `CONTRIBUTING.md` (metadata PRs only; developers host
  their own source and releases).
- License: repository metadata and scripts are MIT (`LICENSE`); each entry
  carries its own upstream license.

`main` holds published content only (README, index, entries, schemas,
scripts, CI, LICENSE). TODO, receipts and evidence live in the OpenAR
repository, never here.
