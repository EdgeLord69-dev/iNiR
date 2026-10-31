# Repository rules for agents

Applies throughout this repository. Read any more-specific `AGENTS.md` before changing its subtree.

## Project and context

- iNiR is a Wayland desktop shell built with Quickshell and Qt Quick/QML, with JavaScript, Bash, Fish, Python, Go, and Nix helpers. Niri is the primary supported/tested compositor; preserve existing guarded Hyprland paths.
- Read `CONTRIBUTING.md` for contributor policy. Use `ARCHITECTURE.md` for runtime boundaries and `STRUCTURE.md` to locate code; load only the sections relevant to the task.
- Read the target code, related tests, and one existing implementation of a similar feature before editing. Verify Quickshell APIs against existing usage or official documentation; do not invent APIs.
- Documentation can lag source. In particular, older contributor examples describe only two families and an incomplete style list, and show a two-argument translation call. Current code has three families and `Translation.tr(text)` takes one argument. Check the owning source before copying examples; surface unresolved conflicts.
- Keep work focused on the requested behavior. Reuse existing services, widgets, and helpers rather than introducing parallel conventions. Do not reformat or restructure unrelated code.

## Architecture map

| Area | Owner / entrypoint |
|---|---|
| Startup and shell-wide IPC | `shell.qml` |
| Shared runtime visibility/state | `GlobalStates.qml` |
| ii composition | `modules/ii/` and `ShellIiPanels.qml` |
| Waffle composition | `modules/waffle/` and `ShellWafflePanels.qml` |
| iRiS composition | `modules/iris/` and `ShellIrisPanels.qml` |
| Config schema and persistence | `modules/common/Config.qml` |
| Reusable UI | `modules/common/widgets/` |
| Runtime services | `services/` and `services/qmldir` |
| CLI and helper processes | `scripts/inir` and `scripts/` |
| Install/update and migrations | `setup` and `sdata/` |
| Shipped configuration | `defaults/` |
| User-facing documentation | `docs/` |

- Families (`ii`, `waffle`, `iris`) are mutually exclusive and switch at runtime. Preserve critical first-frame hosts, deferred family implementations, and on-demand panel loading; do not eagerly instantiate heavy services/panels in the startup path.
- Loader behavior must respect `Config.ready`, enabled panels, family/feature conditions, and the relevant startup/open-state gate.
- Shared infrastructure has shell-wide consumers. Inspect callers before changing `Config`, `Appearance`, `GlobalStates`, `Translation`, `Looks`, or `IrisStyle` contracts.

## QML and visual conventions

- New component files use PascalCase names, one component per file, `id: root`, and `pragma ComponentBehavior: Bound` before imports. Keep singleton pragmas where required. Prefer typed properties over `var` when the shape is known.
- Use the existing `qs.*` imports and module registrations. Register new services in `services/qmldir` and new shared widgets in `modules/common/widgets/qmldir`; follow the local `qmldir` pattern elsewhere.
- IPC handler functions must declare return types, including `: void` for actions.
- Use null-safe access/defaults for runtime objects that may be absent. Schema-declared config properties are typed; optional chaining is allowed, not universally required.
- Use semantic colors, rounding, spacing, and animation tokens, not hardcoded substitutes. Token owners are `modules/common/Appearance.qml` for ii/shared UI, `modules/waffle/looks/Looks.qml` for Waffle, and `modules/iris/style/IrisStyle.qml` for iRiS.
- Global-style detection belongs in `modules/common/Appearance.qml`. Reuse its semantic flags/tokens rather than copying local priority chains; capabilities can overlap.
- Preserve the Qt compatibility floor checked by `scripts/test-qml-qt-compat.py`. QML's JavaScript engine is not a browser or Node.js; do not assume modern JS built-ins are available.
- Comments should explain only non-obvious constraints (engine limits, binding loops, costs, contracts), in one or two lines. Do not narrate the implementation, debugging history, dates, or measurements.

## Configuration, translations, and synchronized changes

Wait for `Config.ready` where initialization depends on loaded user settings. Persist writes through the config API:

```qml
checked: Config.options.bar.autoHide.enable
onToggled: Config.setNestedValue("bar.autoHide.enable", checked)
```

Direct assignment to `Config.options` does not persist. For a new config key, update the schema/runtime fallback in `modules/common/Config.qml`, relevant defaults in `defaults/config.json`, every consumer, and settings surfaces in each family that owns the behavior. Preserve existing user choices and fresh-install defaults deliberately.

- User-visible strings use `Translation.tr("English source text")`; the source text is the lookup key and fallback. Follow the existing `translations/` format and tooling; do not fabricate translations.
- IPC contract changes require `docs/IPC.md` updates. Dependency changes require `docs/PACKAGES.md` and the affected package/distribution manifests.
- Changes to persisted config/data formats need an idempotent migration in `sdata/migrations/`, numbered after the current maximum. Migrations are sourced: no top-level `exit` or `set -e`. Never rename, reorder, or delete existing migrations.
- Update relevant user docs and `CHANGELOG.md` for user-visible behavior changes. Do not bump `VERSION` unless release work is requested.

## Platform and user-state boundaries

- Keep Arch, Fedora, Debian, Void, and Nix paths working. Detect capabilities (`command -v`, usable init/session facilities), not distro names, when choosing runtime behavior. Keep alternate backend paths intact.
- Guard compositor-specific operations with `CompositorService.isNiri` / `CompositorService.isHyprland`. Route power actions through `Session.powerAction` and package updates through `PackageSearch`.
- Use `inir` for shell lifecycle operations. Never manually run bare `qs -c inir` or `qs kill -c inir`; these bypass lifecycle supervision. On systemd setups the shell is managed by `inir.service`; non-systemd backends also exist.
- Editing a checkout is not necessarily editing the running shell: repo-copy, repo-link, and package-managed installations have different payload ownership. Confirm the topology before runtime verification; do not overwrite a packaged installation with setup updates.
- Do not run installation, update, rollback, repair/doctor, migration, or uninstall flows against the user's live environment merely to validate a patch. Use isolated fixtures or obtain explicit approval for state-changing operations.
- Preserve unrelated working-tree changes. Never reset/clean them, edit live user configuration, expose credentials, or commit local state/secrets. Ask before destructive operations outside the requested scope.

## Commands and verification

Run commands from the repository root. Select checks for the changed surface; there is no universal `npm test` or compile step.

| Command | Purpose / limit |
|---|---|
| `bash scripts/inir --help` | Inspect checkout CLI usage without starting the shell |
| `make build` | Set executable permissions; not compilation or validation |
| `bash scripts/test-local-distribution.sh` | Local distribution/lifecycle checks; inspect prerequisites and scope first |
| `make test-local` | Run the local distribution checks after the permission-setting build target |
| `python3 scripts/test-qml-pitfalls.py` | Scan QML for known load/runtime pitfalls; not a full QML engine check |
| `python3 scripts/test-qml-qt-compat.py` | Scan QML/JS for known Qt compatibility problems |
| `python3 scripts/check-distro-parity.py` | Compare branch against `origin/prerelease`; run for distro/init support changes and explain every reported removal |
| `bash -n path/to/changed-script.sh` | Syntax-check changed Bash scripts without executing them |
| `inir restart` | Restart the installed shell through its lifecycle backend; affects the live desktop |
| `inir logs -f` | Follow installed shell logs while exercising a change |

- Find targeted regression checks among `scripts/test-*` and platform checks among `scripts/check-*`; read their entrypoints before running them. Do not treat `scripts/qml-check.fish` as a pass/fail gate: it is a limited recent-file heuristic that always exits zero.
- For bugs, reproduce the reported flow and confirm the fix. For UI changes, exercise the actual affected surface/families and inspect logs; passing scans alone does not prove the component loads or behaves correctly.
- Add regression tests for meaningful behavior/boundaries using the existing conventions, not source-text assertions that merely pin the implementation.
- Report exact commands, observed outcomes, and anything not verified. If no usable desktop/runtime exists, run applicable isolated checks and explicitly state that live UI verification was unavailable.

## Git and delivery

- PRs target `prerelease`, not `main`; development branches start from `prerelease`. Do not switch branches, commit, push, or release without authorization.
- Follow `CONTRIBUTING.md` commit format: `type(scope): what changed`, lowercase, no trailing period, under 60 characters. One logical change per commit; optional body explains why in at most three short lines.
- Do not add bot co-author trailers or generated-with footers. If preparing a PR, disclose AI usage in its checklist as required by the PR template.
- Finish with changed files, behavior, verification evidence, and remaining risks. Leave unrequested adjacent cleanup alone.
