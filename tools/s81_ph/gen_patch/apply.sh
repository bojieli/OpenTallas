#!/bin/bash
# Build the patched S81 generator: the S81-RERUN generator pinned at claude/s81-rerun-20261006 a2e2c5321
# (tools/dsrom_s81_fulldie.py sha256 4d9103ae...) + the CLAUDE S81-PH contract patches given (default all *.patch here).
# Output: tools/_s81ph_gen.py (untracked; parents[1] = repo root so the generator reads this checkout's inputs).
# The patches are default-off: they act only with their env switch (ctrl: OT_S81_PH_CTRL=1).
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd); root=$(cd "$here/../../.." && pwd)
base=a2e2c5321; want=4d9103ae7110ac6e8cd5b9c2a4700399be22ba171fbbaa65921a78c634194757
git -C "$root" fetch -q origin claude/s81-rerun-20261006 2>/dev/null || true
git -C "$root" show $base:tools/dsrom_s81_fulldie.py > "$root/tools/_s81ph_gen.py"
echo "$want  $root/tools/_s81ph_gen.py" | sha256sum -c --quiet
for p in ${@:-$here/*.patch}; do patch -s "$root/tools/_s81ph_gen.py" < "$p"; done
sha256sum "$root/tools/_s81ph_gen.py"
