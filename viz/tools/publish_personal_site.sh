#!/usr/bin/env bash
# Optional mirror of the classroom static site into the personal Pages repo:
#   https://jonathankarr.com/how_the_americas_hear_the_church/
#
# Canonical public deploy is GitHub Pages on this (now public) research repo:
#   https://religion-at-notre-dame.github.io/catholic_media_discourse/
# After the copy, this script commits and pushes the personal Pages repo
# so jonathankarr.com updates without a second manual commit.
# Set PUBLISH_MSG to override the commit message. Set SKIP_PUSH=1 to commit only.
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

# Write the map key into the mirror only. Do not copy it back into this repo.
KEY_FILE="$VIZ/js/basemap-key.js"
if [[ -f "$ROOT/.env" ]]; then
  CARTO_BASEMAP_KEY="$(
    python3 - "$ROOT/.env" <<'PY'
import sys
from pathlib import Path
key = ""
for line in Path(sys.argv[1]).read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    name, _, value = line.partition("=")
    if name.strip() == "CARTO_BASEMAP_KEY":
        key = value.strip().strip('"').strip("'")
print(key, end="")
PY
  )"
fi
CARTO_BASEMAP_KEY="${CARTO_BASEMAP_KEY:-}"
RSYNC_EXCLUDES=(
  --exclude '.cache/'
  --exclude 'tools/'
  --exclude 'serve.py'
  --exclude 'README.md'
  --exclude '.DS_Store'
)
if [[ -n "$CARTO_BASEMAP_KEY" ]]; then
  KEY_FILE="$KEY_FILE" CARTO_BASEMAP_KEY="$CARTO_BASEMAP_KEY" python3 -c 'import os; k=os.environ.get("CARTO_BASEMAP_KEY",""); k=k.replace("\\","\\\\").replace("\"","\\\""); open(os.environ["KEY_FILE"],"w").write("window.CARTO_BASEMAP_KEY = \"%s\";\n" % k)'
  echo "CARTO basemap key written for the personal mirror (not committed here)."
else
  echo "CARTO_BASEMAP_KEY is empty; leaving the mirror's existing basemap key in place." >&2
  RSYNC_EXCLUDES+=(--exclude 'js/basemap-key.js')
fi

mkdir -p "$DEST"
# Replace published payload; keep any local .git if someone nested one (unusual).
rsync -a --delete "${RSYNC_EXCLUDES[@]}" "$VIZ/" "$DEST/"
rm -f "$KEY_FILE"

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

MIRROR_ROOT="$(cd "$(dirname "$DEST")" && pwd)"
SITE_REL="$(basename "$DEST")"
if ! git -C "$MIRROR_ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Mirror is not a git checkout. Nothing was committed." >&2
  exit 1
fi

git -C "$MIRROR_ROOT" add -- "$SITE_REL"
if git -C "$MIRROR_ROOT" diff --cached --quiet; then
  echo "Personal site already matches. No commit."
else
  git -C "$MIRROR_ROOT" commit -m "${PUBLISH_MSG:-Publish the classroom site.}"
  if [[ "${SKIP_PUSH:-0}" != "1" ]]; then
    git -C "$MIRROR_ROOT" push origin HEAD
  fi
fi

echo "Live (after GitHub Pages refreshes):"
echo "  https://jonathankarr.com/how_the_americas_hear_the_church/"
