#!/bin/bash
# Fetch only the hard-core view files (<module>.lef, <module>_tt.lib, <module>_ff.lib) of physical/ref_tile/*/views
# from a git ref into a scratch dir, via `git show` (no checkout; safe on sparse worktrees / a full disk).
#   fetch_core_views.sh REPO REF OUTDIR MODULE[,MODULE...]       e.g.
#   fetch_core_views.sh ~/OpenTallas origin/main ~/scratch/cp2/core_views ot_s81sl_capc5r,ot_s81sl_xrt1
# Output: OUTDIR/<ref_tile dir>/views/<module>/<files>  (the layout pair.py --core-views searches).
set -euo pipefail
REPO=$1; REF=$2; OUT=$3; MODS=$4
for m in ${MODS//,/ }; do
  paths=$(git -C "$REPO" ls-tree -r --name-only "$REF" physical/ref_tile | grep -E "/views/$m/$m(\.lef|_tt\.lib|_ff\.lib)$" || true)
  [ -n "$paths" ] || { echo "fetch_core_views: no views for $m at $REF" >&2; exit 1; }
  for p in $paths; do
    rel=${p#physical/ref_tile/}
    mkdir -p "$OUT/$(dirname "$rel")"
    git -C "$REPO" show "$REF:$p" > "$OUT/$rel"
    echo "$OUT/$rel"
  done
done
