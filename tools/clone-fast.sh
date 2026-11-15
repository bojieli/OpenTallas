#!/bin/bash
# tools/clone-fast.sh -- fast lane checkout of OpenTallas (REPO-STATE-1 11-14)
#
# A full `git clone` fetches all 14k branches plus coord/state history (~11 GB pack) and checks out a multi-GB tree.
# Lanes need one branch and a few directories. Three modes, fastest first:
#
#   tools/clone-fast.sh --from EXISTING_CLONE DIR [--ref REF] [--preset P]
#       git worktree from a clone already on this host: no network, objects shared, seconds. Best when the host has
#       a maintained clone. The worktree dies with that clone (cleanup lanes: keep it while DIR exists).
#   tools/clone-fast.sh DIR [--ref REF] [--preset P]                (default)
#       partial clone: --filter=blob:none --single-branch, then sparse checkout of the preset. Blobs of other paths and
#       old history are fetched on demand (git log -p / blame of an old file goes to GitHub once).
#   tools/clone-fast.sh --coord DIR
#       coord/state only (partial, single branch, full tree; coord/state has no large files of its own in HEAD).
#
# Presets (cone mode; top-level files are always included):
#   tools  tools tests configs schemas spec docs                        (python tools, die/kit scripts, tests)
#   lane   tools tests configs schemas spec docs rtl tb compiler runtime src + physical/* EXCEPT physical/ref_tile
#          (default: RTL + flow lanes). physical/ref_tile is 25.5 GB of the 50 GB HEAD tree; add only the types you
#          need: `git sparse-checkout add physical/ref_tile/<type>`.
#   lane-all  lane + all of physical/ref_tile (measured 11-14: 36 GB, 17 min; avoid)
#   full   everything (no sparse; still a partial blob:none single-branch clone)
#   custom: --preset "dirA dirB ..."
# Later: `git sparse-checkout add results/foo` widens the tree; `git fetch origin other-branch` adds a branch.
# Env: OT_REPO_URL (default git@github.com:bojieli/OpenTallas.git).
set -euo pipefail
URL=${OT_REPO_URL:-git@github.com:bojieli/OpenTallas.git}
FROM=""; REF=""; PRESET="lane"; COORD=0; DIR=""
while [ $# -gt 0 ]; do
  case "$1" in
    --from) FROM="$2"; shift 2;;
    --ref) REF="$2"; shift 2;;
    --preset) PRESET="$2"; shift 2;;
    --coord) COORD=1; shift;;
    -h|--help) sed -n '2,25p' "$0"; exit 0;;
    -*) echo "unknown option $1" >&2; exit 2;;
    *) DIR="$1"; shift;;
  esac
done
[ -n "$DIR" ] || { echo "usage: clone-fast.sh [--from CLONE] [--ref REF] [--preset tools|lane|lane-all|full|\"dirs\"] [--coord] DIR" >&2; exit 2; }
[ -e "$DIR" ] && { echo "$DIR exists" >&2; exit 2; }
DIR=$(realpath -m "$DIR")
[ -z "$FROM" ] || FROM=$(realpath "$FROM")
case "$PRESET" in
  tools) DIRS="tools tests configs schemas spec docs";;
  lane)  DIRS="tools tests configs schemas spec docs rtl tb compiler runtime src @physical-noref";;
  lane-all) DIRS="tools tests configs schemas spec docs rtl tb physical compiler runtime src";;
  full)  DIRS="";;
  *)     DIRS="$PRESET";;
esac
t0=$(date +%s.%N)
sparse() {  # $1 = worktree, $2 = commit whose tree lists physical/* (trees are present even in a blob:none clone)
  [ -n "$DIRS" ] || return 0
  local d=${DIRS/@physical-noref/}
  if [ "$d" != "$DIRS" ]; then
    d="$d $(git -C "$1" ls-tree -d --name-only "$2" physical/ | grep -vx 'physical/ref_tile' | tr '\n' ' ')"
  fi
  git -C "$1" sparse-checkout init --cone
  # shellcheck disable=SC2086
  git -C "$1" sparse-checkout set $d
}
if [ $COORD = 1 ]; then
  git clone -q --filter=blob:none --single-branch --branch coord/state "$URL" "$DIR"
elif [ -n "$FROM" ]; then
  [ -d "$FROM/.git" ] || [ -f "$FROM/HEAD" ] || { echo "--from $FROM is not a clone" >&2; exit 2; }
  # never touch the owner checkout (AGENTS rule: no git in /home/ubuntu/OpenTallas on any host)
  [ "$(readlink -f "$FROM")" != "$(readlink -f /home/ubuntu/OpenTallas)" ] || { echo "refusing --from the owner checkout" >&2; exit 2; }
  git -C "$FROM" fetch -q origin "${REF:-main}" || true
  base=$(git -C "$FROM" rev-parse --verify -q "origin/${REF:-main}" || git -C "$FROM" rev-parse --verify "${REF:-main}")
  git -C "$FROM" worktree add -q --no-checkout --detach "$DIR" "$base"
  sparse "$DIR" "$base"
  git -C "$DIR" checkout -q --detach "$base"
else
  git clone -q --filter=blob:none --single-branch --branch "${REF:-main}" --no-checkout "$URL" "$DIR"
  sparse "$DIR" "origin/${REF:-main}"
  git -C "$DIR" checkout -q "${REF:-main}"
fi
t1=$(date +%s.%N)
printf 'clone-fast: %s ready in %.1f s (%s, preset %s), %s on disk\n' "$DIR" "$(echo "$t1-$t0" | bc)" \
  "$( [ $COORD = 1 ] && echo coord/state || { [ -n "$FROM" ] && echo "worktree of $FROM" || echo partial; } )" "$PRESET" \
  "$(du -sh "$DIR" 2>/dev/null | cut -f1)"
