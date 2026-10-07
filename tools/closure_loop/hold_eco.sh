#!/bin/bash
# closure-loop HOLD-ECO stage (run by closure_loop.py, cwd = the job's src snapshot):
#   hold_eco.sh <route results base (5_2_route.odb)> <sign-off ORFS base (6_final.sdc)> <out dir> <block> [post-SDC (src-rel)...]
# env HM (hold margin ps, default 22), SM (setup margin ps, 25), KEEPCLK (0), MACROS (src-rel macro view dirs), THREADS (8)
# -> <out>/eco.log, <out>/orfs/results/asap7/<d>/base/6_final.{odb,spef,v,sdc}, <out>/corner_sta.json (tools/w18/corner_sta.py
#    with the same post-SDCs), <out>/result.json {ss_ps, ff_ps, drc, cells_added}
set -eo pipefail
RB=$1; OB=$2; OUT=$3; BLK=$4; shift 4
D=$(basename $(dirname $RB)); EB=$OUT/orfs/results/asap7/$D/base
[ ! -e "$OUT" ] || { echo "ECO output already exists; preserving evidence: $OUT"; exit 10; }
if [ -n "${ECO_GUARD:-}" ]; then python3 "$(dirname "$0")/eco_recovery.py" verify "$ECO_GUARD"; fi
mkdir -p "$EB"
cp $OB/6_final.sdc $EB/6_final.sdc
DB=5_2_route.odb; [ -f $RB/$DB ] || DB=6_final.odb   # pre-fill route db; the tcl removes fillers otherwise
echo "ECO input $RB/$DB"
PS=""; for p in "$@"; do PS="$PS /src/$p"; done
MS=""; for m in ${MACROS:-}; do MS="$MS /src/$m"; done
docker run --rm -v $RB:/in:ro -v $EB:/out -v $PWD:/src:ro -v $(cd $(dirname $0) && pwd):/cl:ro \
  -e OT_DB=/in/$DB -e OT_SDC=/out/6_final.sdc -e OT_OUT=/out -e OT_POST_SDC="${PS# }" -e OT_MACROS="${MS# }" \
  -e OT_HOLD_MARGIN=${HM:-22} -e OT_SETUP_MARGIN=${SM:-25} -e OT_KEEP_CLOCK=${KEEPCLK:-0} -e OT_THREADS=${THREADS:-8} \
  -e OT_MAXL=${MAXL:-M7} -e OT_MAX_BUF_PCT=${BUF:-10} openroad/orfs:latest bash -lc \
  "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /cl/hold_eco.tcl" > $OUT/eco.log 2>&1
grep -q "OT_ECO done" $OUT/eco.log || { echo "ECO failed (no OT_ECO done)"; tail -20 $OUT/eco.log; exit 9; }
python3 tools/w18/corner_sta.py $(for p in "$@"; do echo -n " --post-sdc $p"; done) $(for m in ${MACROS:-}; do echo -n " --macro $m"; done) \
  --orfs-dir $OUT/orfs --output $OUT/corner_sta.json > $OUT/corner.log 2>&1 || { echo "corner_sta failed"; tail $OUT/corner.log; exit 8; }
python3 - $OUT <<'PY'
import json, re, sys
o = sys.argv[1]
log = open(f'{o}/eco.log').read()
nv = re.findall(r'Number of violations = (\d+)', log)
cs = json.load(open(f'{o}/corner_sta.json'))
add = re.findall(r'OT_ECO cells_added (-?\d+)', log)
r = dict(ss_ps=cs['setup_ss']['worst_slack_ps'], ff_ps=cs['hold_ff']['worst_slack_ps'], drc=int(nv[-1]) if nv else None,
         cells_added=int(add[0]) if add else None, errors=cs['setup_ss'].get('errors', []) + cs['hold_ff'].get('errors', []))
json.dump(r, open(f'{o}/result.json', 'w'), indent=1); print(json.dumps(r))
PY
