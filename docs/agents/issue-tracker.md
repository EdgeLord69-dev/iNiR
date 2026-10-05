# Issue tracker: Local Markdown

Issues and specs live as Markdown files in `.scratch/`.

## Conventions

- One feature per directory: `.scratch/<feature-slug>/`.
- Spec: `.scratch/<feature-slug>/spec.md`.
- Tickets: `.scratch/<feature-slug>/issues/<NN>-<slug>.md`,
  numbered from `01`, one file per ticket.
- Triage state: a `Status:` line near the top, using the
  role strings in `triage-labels.md`.
- Conversation: append under `## Comments`.

## Publish or fetch tickets

To publish a ticket, create its file in the feature's `issues/`
directory. To fetch a ticket, read its referenced file; resolve
bare numbers within the relevant feature directory.

## Wayfinding operations

- Map: `.scratch/<effort>/map.md`, containing Notes,
  Decisions-so-far, and Fog.
- Children: numbered files in `.scratch/<effort>/issues/`.
- Type: a `Type:` line (`research`, `prototype`, `grilling`, or `task`).
- Wayfinding state: `Status: claimed` or `Status: resolved`.
- Blocking: `Blocked by: NN, NN`; unblocked when all listed
  tickets are resolved.
- Frontier: first open, unblocked, unclaimed ticket by number.
- Claim: save `Status: claimed` before starting work.
- Resolve: append the answer under `## Answer`, save
  `Status: resolved`, and append a gist and link to the map's
  Decisions-so-far.
