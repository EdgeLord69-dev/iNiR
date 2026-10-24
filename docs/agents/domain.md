# Domain Docs

## Before exploring

This repository uses a single-context layout.

- Read root `GLOSSARY.md` when present.
- Read ADRs in `docs/adr/` relevant to the area being explored.

If either is absent, proceed silently. Domain modeling creates documentation
lazily when terms or decisions are resolved; missing docs need no upfront action.

## Layout

- `GLOSSARY.md`: repository-wide domain vocabulary.
- `docs/adr/`: repository-wide architecture decisions; preserve existing ADRs.

## Use the glossary's vocabulary

Use glossary terms when naming domain concepts in issue titles, proposals,
hypotheses, and tests. Respect explicitly avoided synonyms.

If a needed concept is missing, reconsider whether it matches project language;
note genuine gaps for `/domain-modeling`.

## Flag ADR conflicts

Explicitly surface proposals that contradict an existing ADR, naming the ADR
and explaining why the decision should be revisited.
