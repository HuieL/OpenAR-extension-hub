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
- **Event details and repeats.** Events can carry a location and notes, and a
  daily, weekly, monthly or yearly repeat (interval, occurrence count or end
  date, weekday selection for weekly rules, per-date exceptions). Repeats
  expand only inside the requested window, a repeat needs a start, and a
  series that hits the expansion bound is reported as truncated, never
  guessed. Days and weeks stay honest the same way: busy checks include
  occurrences that start before the window, with their own truncation count.
- **Local calendars.** Events can carry an optional calendar label (up to
  sixteen local calendars, label at most sixty-four bytes); an event without a
  label stays on your primary calendar, and the editor offers the labels you
  already use.
- **Range search.** Read any explicit start-to-end range instead of a fixed
  day or week: the end date is exclusive, the span is bounded to 366 days,
  and the same honest placement, truncation and exclusion counts apply.
- **One window, several sources.** The unified day/week window reads your
  events, the deadlines source layer (below), and a read-only CCF conference
  deadline snapshot embedded from one pinned upstream commit, plus the
  projected rows of the subscribed feeds below that have a proven body. Each
  source keeps its own revision and status; disabling one degrades only that
  layer, and row counts are reported instead of silently truncated.
- **Deadline watches.** Optional personal reminder rules over both layers:
  bounded offsets, bindings pinned to a content signature, one audited
  transition per replan, and submitted state or private notes that source
  updates never overwrite. No precise reminder is generated for TBD or
  unresolved times. Due watches fire through the host's shared reminder
  engine: candidates pass the same quiet-hours, quota and snooze policy as
  personal reminders, delivery is at-least-once, rescheduling a stage lets
  its old reminder keys lapse naturally, and a disabled instance delivers
  nothing.
- **Deadline filtering.** The conference layer can be narrowed before the
  window budgets apply: a case-insensitive title query, a CCF rank
  selection and a direction (subfield) selection combine into one filter.
  Stages dropped by it are counted as filtered out rather than silently
  missing, and the active filter is echoed back with the read so the display
  always shows what was asked.
- **ICS preview.** A bounded read-only `ics.parse` previews untrusted
  iCalendar text: supported repeats expand within the requested window,
  unsupported rule parts degrade to the master occurrence with reported
  issues, and parsing imports nothing.
- **ICS subscriptions.** Store a bounded list of calendar addresses;
  `subscription.refresh` fetches one feed on demand with ETag/Last-Modified
  conditional requests, reports unchanged content as not-modified, keeps the
  last successful sync separate from failed attempts, and never imports
  fetched events automatically. Fetched events overlay the unified read as a
  separate read-only layer only after a fetch succeeded: each feed shows its
  own honest state (pending, stale, unavailable), rows come from the last
  stored proven body rather than the raw feed text, and nothing is imported
  into your manual events. The calendar panel manages the list — add, label,
  remove and refresh — and untrusted feed content never gains write access.
- **Preparation blocks.** Bounded work blocks linked to a deadline marker —
  they never modify the official deadline time. `busy` answers conflict
  checks by merging precise zoned intervals of records and blocks; entries
  without precise times are reported as excluded, never inferred, and
  deadlines themselves are due points, never busy time.
- **Research focus.** Pin up to three research goals: a project with a
  concrete deadline point, either a labeled manual time or a stage from the
  read-only CCF snapshot. A TBD stage honestly stays "to be announced" —
  no countdown is invented — and a deadline whose time moved is reported as
  moved. Goals carry their own milestones (title, due point, done, note);
  marking a milestone done keeps its identity, and a preparation block can
  link to a pinned goal the same way it links to a deadline marker, without
  ever touching the official deadline.

## Deadlines

The [Deadlines extension](../openra.deadlines/about/README.md) keeps its own
id and remains the place to manage deadline sources directly. Calendar reads
those same records as its default deadline source layer, so your existing
data, deep links and permissions keep working; official deadline times are
read-only in the calendar, which offers preparation blocks instead of edits.
