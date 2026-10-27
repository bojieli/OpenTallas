#!/bin/bash
# QC-CORES-4 BTAB R10 continuation (after the FF data-hold ECO trial 6e6e8f16b234, CQB_HOLD_AFTER +4.68 / 0 endpoints):
# DRT + fill + finish + report (ORFS RCX 6_final.spef) on the post-hold GRT checkpoint of the same kit, then the uniform
# sign-off (signoff.py run tt,ff, tools of the kit's source commit, bundled at $K/so_r10/tools/die_plan) and the routed
# LEC (lec.py of the same commit) on 6_final.v.  No clock edits, no period/uncertainty change, no further hold repair.
#   btab_r10_route.sh KITDIR
set -uo pipefail
K=$(cd "$1" && pwd); IMG=openroad/orfs:asap7lock; SO=$K/so_r10/tools/die_plan
st() { echo "R10RT $1 $(date -Is)" | tee -a "$K/r10_route_chain.txt"; }
M='make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8'
grep -q BTAB_R10_FF_DONE "$K/r10_ff.log" || { st "NO_FF_HOLD_CHECKPOINT"; exit 2; }
test -f "$SO/signoff.py" -a -f "$SO/lec.py" || { st "NO_TOOLS $SO"; exit 2; }
st "start"
docker run --rm --name btr10-rt-$$ --cpus=8 --memory=24g --memory-swap=24g -v "$K":/work -w /OpenROAD-flow-scripts/flow $IMG bash -lc \
  "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; rc=0; for t in do-5_2_route do-5_3_fillcell do-5_route do-5_route.sdc do-6_1_fill do-6_1_fill.sdc do-6_report; do $M \$t || { rc=\$?; echo STAGE_FAIL \$t rc \$rc; break; }; done; chown -R $(id -u):$(id -g) /work/run; exit \$rc" > "$K/route_r10.log" 2>&1; rc=$?
st "ROUTE rc $rc $(grep -h 'Number of violations' $K/route_r10.log | tail -1)"; [ $rc = 0 ] || exit 4
SIGNOFF_DOCKER=docker python3 -I "$SO/signoff.py" run --run-dir "$K/run" --kit "$K" --out "$K/signoff_r10" --corners tt,ff --image $IMG > "$K/signoff_r10.log" 2>&1; so=$?
st "signoff rc $so $(grep -h ^SIGNOFF $K/signoff_r10.log | head -1)"
B=$(ls -d $K/run/results/asap7/*/base | head -1)
docker run --rm -m 24g --cpus 8 -v "$K":/work:ro -v "$B":/n:ro -v "$SO":/m:ro -v "$K/lec_r10":/o $IMG bash -lc \
  "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 -I /m/lec.py /work --netlist /n/6_final.v --out /o; rc=\$?; chown -R $(id -u):$(id -g) /o; exit \$rc" > "$K/lec_r10.log" 2>&1; lr=$?
st "lec rc $lr $(tail -1 $K/lec_r10.log | cut -c1-200)"
st "CHAIN_DONE"
[ $so = 0 ] && [ $lr = 0 ]
