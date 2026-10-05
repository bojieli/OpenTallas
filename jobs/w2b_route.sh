#!/bin/bash
# usage: jobs/w2b_route.sh <case> <tag> <keepdir> <output-json> -- (runs from worktree root on the worker)
set -uo pipefail
CASE=$1; TAG=$2; KEEP=$HOME/$3; OUT=$4   # KEEP relative to $HOME (not an absolute gate argument)
WT=$(pwd)
ARGV=$(python3 tools/v41_w2_romac_pnr.py "$CASE" --tag "$TAG" --keep "$KEEP" --output "$OUT" --print | python3 -c "import json,sys,shlex;print(' '.join(shlex.quote(a) for a in json.load(sys.stdin)['argv']))")
mkdir -p "$(dirname "$KEEP")"; docker run --rm -v "$(dirname "$KEEP"):/w" alpine rm -rf "/w/$(basename "$KEEP")"
eval python3 $ARGV --force
rc=$?
echo "ROUTE_RC=$rc"
DEST=$(dirname "$OUT")/${TAG}_views
mkdir -p "$DEST"
[ -d "$KEEP/orfs" ] && CASEDIR="$KEEP/orfs" || CASEDIR="$KEEP"
NICK=$(ls "$CASEDIR/results/asap7" | head -1)
BASE="$CASEDIR/results/asap7/$NICK/base"
if [ -f "$BASE/6_final.odb" ]; then
  docker run --rm -v "$WT:/src:ro" -v "$CASEDIR:/work" -w /OpenROAD-flow-scripts/flow ${OPENTALLAS_ORFS_IMAGE:-openroad/orfs:latest} bash -lc \
   "trap 'chmod -R a+rwX /work >/dev/null 2>&1 || true' EXIT; source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base do-generate_abstract" > "$CASEDIR/abstract.log" 2>&1
  echo "ABSTRACT_RC=$?"
  cp "$CASEDIR/abstract.log" "$DEST/" 2>/dev/null
  cp "$BASE"/*.lef "$BASE"/*_typ.lib "$DEST/" 2>/dev/null
fi
# small evidence: reports and logs (no ODB/DEF)
for d in reports logs; do
  [ -d "$CASEDIR/$d/asap7/$NICK/base" ] && mkdir -p "$DEST/$d" && cp "$CASEDIR/$d/asap7/$NICK/base"/*.{rpt,log,json} "$DEST/$d/" 2>/dev/null
done
cp "$CASEDIR"/config.mk "$CASEDIR"/constraint.sdc "$CASEDIR"/io_constraints.tcl "$DEST/" 2>/dev/null
exit $rc
