#!/bin/bash
# usage (inside ot-run, from the repo worktree root): tools/hbm_b2/q3sync/edge_sched.sh <OUT> [variant]
#   variant: pass (default) | illegal_empty (negative: publish with no lane) | mut_min (negative: both cores pick min)
# Rule 3: refuses a dirty tracked tree; every input is repo-relative at HEAD; the __q3sync copies are regenerated
# from tools/hbm_b2/q3sync/q3_sync_profile.py at HEAD into <OUT>/gen (never read from an older scratch dir).
set -u
OUT=$1; VAR=${2:-pass}; RUNS=${RUNS:-400}; SEED=${SEED:-1}
WT=$(git rev-parse --show-toplevel) || exit 2
cd "$WT"
if [ -n "$(git status --porcelain --untracked-files=no)" ]; then echo "DIRTY tracked tree: refuse"; exit 2; fi
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
mkdir -p "$OUT"; D=$OUT/$VAR; rm -rf "$D"; mkdir -p "$D"
git rev-parse HEAD > "$OUT/source_commit.txt"
if [ ! -f "$OUT/gen/.done" ]; then
  rm -rf "$OUT/gen"
  python3 -I tools/hbm_b2/q3sync/q3_sync_profile.py --root . --files tools/hbm_b2/q3sync/q3b.files --out "$OUT/gen" \
     --census "$OUT/census_regen.json" > "$OUT/gen.log" 2>&1 || { echo "GEN FAIL"; exit 2; }
  touch "$OUT/gen/.done"
fi
CEN=results/token_pass/path_hbm_1713/q3sync/census.json
gen=$(python3 -c "import json;c=json.load(open('$CEN'));print(' '.join('$OUT/gen/'+f for f in c['core_filelists']['edge']['files']))")
leg=$(python3 -c "
import json;c=json.load(open('$CEN'));fl=set(c['core_filelists']['edge']['files'])
print(' '.join(e['source'] for e in c['emitted'] if e['emitted'] in fl))")
mac=$(python3 -c "import json;c=json.load(open('$CEN'));print(' '.join(c['core_filelists']['edge']['macros']))")
DEF=""; [ $VAR = illegal_empty ] && DEF="-DILLEGAL_EMPTY"; [ $VAR = mut_min ] && DEF="+define+OT_COLL_AMX_MUT_MIN"
python3 -I tools/hbm_b2/q3sync/q3_edge_sched_tb.py rtl/hbm_accel/cores_split/ot_hfd_coll_q3_hard_v8x/ot_hfd_coll_q3_edge_core.sv \
   --out "$D/tb.sv" --runs $RUNS --seed $SEED > "$D/tbgen.log"
log=$D/sim.log
echo "# $(date) host=$(hostname) commit=$(git rev-parse HEAD) variant=$VAR runs=$RUNS seed=$SEED" > $log
sha256sum $leg $mac rtl/hbm_accel/cores_split/ot_hfd_coll_q3_hard_v8x/ot_hfd_coll_q3_edge_core.sv > "$D/inputs.sha256"
(cd $OUT/gen && sha256sum $(python3 -c "import json;c=json.load(open('$WT/$CEN'));print(' '.join(c['core_filelists']['edge']['files']))")) > "$D/gen.sha256"
$V --binary --timing -j 2 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN $DEF --Mdir $D/obj --top-module tb \
   $D/tb.sv $leg $gen $mac > $D/build.log 2>&1
brc=$?; echo "# build rc=$brc" >> $log
[ $brc = 0 ] && { $D/obj/Vtb +verilator+seed+$SEED >> $log 2>&1; echo "# sim rc=$? $(date)" >> $log; }
rm -rf $D/obj
grep -E "^EDGE_SCHED" $log
