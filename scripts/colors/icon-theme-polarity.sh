#!/usr/bin/env bash
# Give a dark icon theme back the icons it borrows from its light sibling.
#   icon-theme-polarity.sh <theme>
# Some dark variants link whole folders to the light theme (WhiteSur-dark's mimes/16 -> WhiteSur/mimes/16), so a
# GTK 3 file chooser draws every folder in the light theme's #363636 on a dark view. For each linked folder, the
# icons drawn in the light sibling's text colour are written, in the dark theme's own text colour, to the same
# theme name under the user's icons (GTK merges a theme across its search paths). Nothing outside it is touched.
set -euo pipefail

theme="${1:-}"
[[ "$theme" == *-dark || "$theme" == *-Dark ]] || exit 0
light="${theme%-*}"

find_theme() {
    local dir
    IFS=':' read -r -a dirs <<< "${XDG_DATA_DIRS:-/usr/local/share:/usr/share}"
    for dir in "${dirs[@]}"; do
        [[ -f "$dir/icons/$1/index.theme" ]] && { printf '%s\n' "$dir/icons/$1"; return 0; }
    done
    return 1
}

dark_dir="$(find_theme "$theme")" || exit 0
light_dir="$(find_theme "$light")" || exit 0
overlay="${XDG_DATA_HOME:-$HOME/.local/share}/icons/$theme"

# The text colour each theme declares on its own (non-linked) folder icon.
text_colour() {
    grep -ho 'ColorScheme-Text *{ *color: *#[0-9A-Fa-f]\{6\}' "$1"/places/16/folder.svg 2>/dev/null | grep -o '#[0-9A-Fa-f]\{6\}' | head -n1
}
light_text="$(text_colour "$light_dir")"
dark_text="$(text_colour "$dark_dir")"
[[ -n "$light_text" && -n "$dark_text" && "${light_text,,}" != "${dark_text,,}" ]] || exit 0

stamp="$overlay/.inir-polarity"
signature="$light_text $dark_text $(stat -c %Y "$dark_dir" "$light_dir" | tr '\n' ' ')"
[[ -f "$stamp" && "$(cat "$stamp")" == "$signature" ]] && exit 0

for link in "$dark_dir"/*/*; do
    [[ -L "$link" ]] || continue
    target="$(readlink -f "$link")"
    [[ "$target" == "$light_dir"/* ]] || continue
    rel="${link#"$dark_dir"/}"
    while IFS= read -r -d '' icon; do
        out="$overlay/$rel/${icon#"$target"/}"
        mkdir -p "$(dirname "$out")"
        sed "s/${light_text}/${dark_text}/Ig" "$icon" > "$out"
    done < <(grep -RlZ --include='*.svg' -i "color: *${light_text}" "$target"/ 2>/dev/null || true)
done
mkdir -p "$overlay"
printf '%s\n' "$signature" > "$stamp"
