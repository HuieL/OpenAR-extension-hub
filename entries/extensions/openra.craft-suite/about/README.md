# Craft Suite

Choose optional editing components for documents and figures.

**Delivery: bundled.** The code ships inside the OpenAR app. Installing this
entry from the Extension Hub switches it on for you; nothing is downloaded or
run from this repository. Uninstalling turns it off everywhere and keeps
everything it saved, so a later reinstall picks up where you left off.

The entry's `version` must match the version the app ships; an app that
ships another version refuses the install and asks you to update the app or
pick the matching entry.

## Components

Craft Suite is one entry with optional components. Installing the suite does
**not** install them: each component runs its own engine, an open-source app
from the [Craft App Suite](https://github.com/storytold), and you install,
update or roll back each one separately from the Craft Suite page. Every
engine is a fixed release, checked against its published checksum before it
is unpacked, and installed only after you approve the exact downloaded files;
nothing updates on its own. Which builds exist for your computer is shown on
the page.

| Component | Engine | Upstream | Pinned release |
|---|---|---|---|
| Photos | PhotoCraft | [storytold/photocraft](https://github.com/storytold/photocraft) | v0.3.0 |
| Vector graphics | VectorCraft | [storytold/vectorcraft](https://github.com/storytold/vectorcraft) | v0.4.0 |
| PDF | PrintCraft | [storytold/pdfcraft](https://github.com/storytold/pdfcraft) | v0.2.1 |
| Sheets | GridCraft | [storytold/gridcraft](https://github.com/storytold/gridcraft) | v0.1.0 |
| Slides | DeckCraft | [storytold/deckcraft](https://github.com/storytold/deckcraft) | v0.1.0 |
| Layout | DesignCraft | [storytold/designcraft](https://github.com/storytold/designcraft) | v0.2.1 |
| Video | FilmCraft | [storytold/filmcraft](https://github.com/storytold/filmcraft) | v0.2.1 |
| Motion | EffectCraft | [storytold/effectcraft](https://github.com/storytold/effectcraft) | v0.4.0 |
| Photo library | LightCraft | [storytold/lightcraft](https://github.com/storytold/lightcraft) | v0.2.1 |
| Documents | WordCraft | [storytold/wordcraft](https://github.com/storytold/wordcraft) | v0.7.0 |
| Audio | SoundCraft | [storytold/soundcraft](https://github.com/storytold/soundcraft) | v0.3.0 |
| CAD | CADCraft | [storytold/cadcraft](https://github.com/storytold/cadcraft) | v0.1.0 |

The first release works on your own photos, PDFs, CSV tables and vector
drawings; the other components are offered once their formats are supported
for your own files.

Engines are MIT OR Apache-2.0, like each Craft app; their authors are the
ArtCraft Team and each app's contributors.
