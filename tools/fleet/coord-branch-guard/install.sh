#!/bin/bash
# usage: install.sh [WORKTREE]   (default /home/ubuntu/coord)    COORD 11-19: guard the hub-coord worktree against a branch switch.
# Copies the hooks to $HOME/.local/lib/coord-guard/hooks (copy + mv) and points ONLY that linked worktree at them through its own
# config.worktree (the repo has extensions.worktreeConfig = true).  No git command is run in the worktree.
set -eu
W=${1:-/home/ubuntu/coord}
H=$(cd "$(dirname "$0")" && pwd)
D=${COORD_GUARD_DIR:-$HOME/.local/lib/coord-guard/hooks}
gd=""; [ -f "$W/.git" ] && gd=$(sed -n 's/^gitdir: //p' "$W/.git")
[ -n "$gd" ] && [ -d "$gd" ] || { echo "install.sh: $W is not a linked worktree (no gitdir: line in $W/.git)" >&2; exit 1; }
common=$(cd "$gd" && cd "$(cat commondir)" && pwd)
grep -Eq '^[[:space:]]*worktreeConfig[[:space:]]*=[[:space:]]*true' "$common/config" || { echo "install.sh: extensions.worktreeConfig is not true in $common/config" >&2; exit 1; }
mkdir -p "$D"
for f in post-checkout pre-push; do cp "$H/$f" "$D/$f.new"; chmod 755 "$D/$f.new"; mv "$D/$f.new" "$D/$f"; done
cfg="$gd/config.worktree"
if [ -f "$cfg" ] && grep -q 'hooksPath' "$cfg"; then
  grep -q "hooksPath *= *$D\$" "$cfg" || { echo "install.sh: $cfg already sets another core.hooksPath; not touched" >&2; exit 1; }
else
  { [ -f "$cfg" ] && cat "$cfg"; printf '[core]\n\thooksPath = %s\n' "$D"; } > "$cfg.new"
  mv "$cfg.new" "$cfg"
fi
echo "coord-branch-guard installed: hooks in $D, worktree $W ($gd/config.worktree)"
