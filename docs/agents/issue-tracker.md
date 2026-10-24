# Issue tracker: Local Markdown

Issues and specs for this repo live as Markdown files in `.scratch/`.

## Conventions

- One feature per directory: `.scratch/<feature-slug>/`.
- Spec: `.scratch/<feature-slug>/spec.md`.
- Implementation tickets: `.scratch/<feature-slug>/issues/<NN>-<slug>.md`,
  numbered from `01`, one file per ticket.
- Triage state: a `Status:` line near the top of each issue file.
  Use the role strings in `triage-labels.md`.
- Append comments and conversation history under `## Comments`.

## Publishing and fetching

When asked to publish to the issue tracker, create the appropriate spec
or ticket file using the conventions above, creating directories as needed.

When asked to fetch a ticket, read the referenced file. Resolve a bare
ticket number within the relevant feature directory.

## Wayfinding operations

Used by `/wayfinder`:

- Map: `.scratch/<effort>/map.md`, holding Notes / Decisions-so-far / Fog.
- Child ticket: `.scratch/<effort>/issues/NN-<slug>.md`, numbered from `01`,
  with the question in the body and a `Type:` line:
  `research`, `prototype`, `grilling`, or `task`.
- Workflow state: `Status: claimed` or `Status: resolved` for claimed or
  completed wayfinding tickets; these are workflow states, not triage roles.
- Blocking: `Blocked by: NN, NN` near the top. A ticket is unblocked when
  every listed ticket is resolved.
- Frontier: scan for open, unblocked, unclaimed tickets; first by number wins.
- Claim: set `Status: claimed` and save before any work.
- Resolve: append the answer under `## Answer`, set `Status: resolved`,
  then append a gist and link to the map's Decisions-so-far.
