# Domain docs

## Before exploring

Read root `GLOSSARY.md` and ADRs in `docs/adr/` relevant to
the area being explored.

If these do not exist, proceed silently. Domain-modeling
creates them lazily when terms or decisions are resolved.

## Layout

Single-context:
- `GLOSSARY.md`: shared domain vocabulary.
- `docs/adr/`: architectural decision records.

## Vocabulary

Use glossary terms in issue titles, proposals, hypotheses,
and test names. Respect explicitly avoided synonyms.

If a needed concept is missing, reconsider invented language
or note the gap for domain-modeling.

## ADR conflicts

Surface contradictions explicitly, naming the ADR and why
its decision may be worth reopening.
