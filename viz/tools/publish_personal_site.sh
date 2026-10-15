#!/usr/bin/env bash
# Optional mirror of the classroom static site into the personal Pages repo:
#   https://jonathankarr.com/how_the_americas_hear_the_church/
#
# Canonical public deploy is GitHub Pages on this (now public) research repo:
#   https://religion-at-notre-dame.github.io/catholic_media_discourse/
# This script does not commit or push; review then commit in the personal repo.
set -euo pipefail

TOOLS="$(cd "$(dirname "$0")" && pwd)"
VIZ="$(cd "$TOOLS/.." && pwd)"
ROOT="$(cd "$VIZ/.." && pwd)"

DEST="${DEST:-}"
if [[ -z "$DEST" ]]; then
  for candidate in \
    "$ROOT/../JonathanKarr33.github.io/how_the_americas_hear_the_church" \
    "$HOME/Documents/JonathanKarr33.github.io/how_the_americas_hear_the_church"; do
    parent="$(dirname "$candidate")"
    if [[ -d "$parent/.git" ]] || [[ -d "$parent" ]]; then
      DEST="$candidate"
      break
    fi
  done
fi

if [[ -z "${DEST:-}" ]]; then
  echo "Could not find JonathanKarr33.github.io. Set DEST=/path/to/how_the_americas_hear_the_church" >&2
  exit 1
fi

if [[ "${SKIP_CHECK:-0}" != "1" ]]; then
  echo "== check.sh =="
  bash "$TOOLS/check.sh"
fi

mkdir -p "$DEST"
# Replace published payload; keep any local .git if someone nested one (unusual).
rsync -a --delete \
  --exclude '.cache/' \
  --exclude 'tools/' \
  --exclude 'serve.py' \
  --exclude 'README.md' \
  --exclude '.DS_Store' \
  "$VIZ/" "$DEST/"

# Ensure Pages does not run Jekyll on the mirror either.
touch "$DEST/.nojekyll"

# Short README for the published folder (no private-repo paths).
cat > "$DEST/README.md" <<'EOF'
# How the Americas Hear the Church

Public classroom site mirror.

**Live:** https://jonathankarr.com/how_the_americas_hear_the_church/

Open [`index.html`](index.html) (redirects to [`pages/index.html`](pages/index.html)).
Source of truth is the research repository; republish with the viz publish script there.
EOF

echo "Published static site → $DEST"
echo "Public URL (after push to JonathanKarr33.github.io):"
echo "  https://jonathankarr.com/how_the_americas_hear_the_church/"
echo "Next: cd \"$(dirname "$DEST")\" && git status && commit/push when ready."
