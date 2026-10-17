# iNiR

A complete desktop shell for Niri, built with Quickshell and QML.

It provides the bar, dock, sidebars, notifications, settings, wallpapers, overview, lock screen, IPC and theming in one shell. Niri is the supported and tested compositor; legacy Hyprland compatibility paths remain from the original fork.

## Start here

- [Install](INSTALL.md)
- [Setup, updates and rollback](SETUP.md)
- [Keybinds](KEYBINDS.md)
- [IPC reference](IPC.md)
- [Panel families](PANEL_FAMILIES.md)
- [iRiS](IRIS.md)
- [Configuration](CONFIG_SYSTEM.md)
- [Known limitations](LIMITATIONS.md)
- [Managed desktop items](DESKTOP_ITEMS.md)
- [Void Linux](VOID.md)

## Common commands

```bash
inir run
inir restart
inir settings
inir logs
inir doctor
inir update
```

## Branches

`main` is the stable branch used by installations and updates.

`prerelease` is where development happens. It may be ahead by a lot. That is the point.

## Runtime shape

```text
Niri
  -> Quickshell
  -> shell.qml
  -> shared config and services
  -> ii, Waffle, or iRiS
  -> panels, overlays and widgets
```

The shell is configurable through Settings and `config.json`. Persistent writes go through the config service; editing QML is not part of normal use.

## Reference

| Area | Page |
|---|---|
| Installation and packages | [Install](INSTALL.md), [Packages](PACKAGES.md) |
| Void Linux | [Void guide](VOID.md), [Capability matrix](VOID_CAPABILITIES.md) |
| Runtime and architecture | [Runtime](RUNTIME.md), [Architecture](ARCHITECTURE_OVERVIEW.md), [Project map](PROJECT_MAP.md) |
| iRiS | [iRiS family guide](IRIS.md), [Panel families](PANEL_FAMILIES.md) |
| Services and modules | [Services](SERVICES.md), [Modules](MODULES.md), [Global actions](GLOBAL_ACTIONS.md) |
| Wallpapers and theming | [Wallpaper](WALLPAPER.md), [Theming](THEMING_ARCHITECTURE.md), [Targets](THEMING_TARGETS.md), [Presets](THEMING_PRESETS.md), [Theming modules](THEMING_MODULES.md) |
| Desktop references | [Managed desktop items](DESKTOP_ITEMS.md), [Notifications](NOTIFICATIONS.md), [Calendar](CALENDAR.md), [Autostart](AUTOSTART.md), [Audio and media](AUDIO_MEDIA.md) |
| Compositor support | [Compositors](COMPOSITORS.md) |
| NixOS | [NixOS guide](NIXOS.md) |
| Performance | [Optimization](OPTIMIZATION.md) |

If the documentation disagrees with the current shell, the shell wins. Then the documentation gets fixed.
