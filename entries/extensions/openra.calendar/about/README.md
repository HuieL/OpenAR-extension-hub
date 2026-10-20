# Calendar

A unified local calendar: your events and day/week agendas, with your
deadlines as a source layer.

**Delivery: bundled.** The code ships inside the OpenAR app. Installing this
entry from the Extension Hub switches it on for you; nothing is downloaded or
run from this repository. Uninstalling turns it off everywhere and keeps
everything it saved, so a later reinstall picks up where you left off.

The entry's `version` must match the version the app ships; an app that
ships another version refuses the install and asks you to update the app or
pick the matching entry.

## What it does

- **Events.** Save manual events with stable IDs; concurrent saves are caught
  by revision conflicts. Original timezones, all-day and floating times stay
  distinct; ambiguous or unknown times are flagged for review instead of
  guessed.
- **One window, several sources.** The unified day/week window reads your
  events, the deadlines source layer (below), and a read-only CCF conference
  deadline snapshot embedded from one pinned upstream commit. Each source
  keeps its own revision and status; disabling one degrades only that layer,
  and row counts are reported instead of silently truncated.
- **Deadline watches.** Optional personal reminder rules over both layers:
  bounded offsets, bindings pinned to a content signature, one audited
  transition per replan, and submitted state or private notes that source
  updates never overwrite. No precise reminder is generated for TBD or
  unresolved times. The reminder engine is not wired, so saved rules schedule
  nothing yet.
- **ICS preview.** A bounded read-only `ics.parse` previews untrusted
  iCalendar text: supported repeats expand within the requested window,
  unsupported rule parts degrade to the master occurrence with reported
  issues, and parsing imports nothing.
- **ICS subscriptions.** Store a bounded list of calendar addresses;
  `subscription.refresh` fetches one feed on demand with ETag/Last-Modified
  conditional requests, reports unchanged content as not-modified, keeps the
  last successful sync separate from failed attempts, and never imports
  fetched events automatically.
- **Preparation blocks.** Bounded work blocks linked to a deadline marker —
  they never modify the official deadline time. `busy` answers conflict
  checks by merging precise zoned intervals of records and blocks; entries
  without precise times are reported as excluded, never inferred, and
  deadlines themselves are due points, never busy time.

## Deadlines

The [Deadlines extension](../openra.deadlines/about/README.md) keeps its own
id and remains the place to manage deadline sources directly. Calendar reads
those same records as its default deadline source layer, so your existing
data, deep links and permissions keep working; official deadline times are
read-only in the calendar, which offers preparation blocks instead of edits.
