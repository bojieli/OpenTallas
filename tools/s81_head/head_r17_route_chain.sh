#!/bin/bash
# HEAD-CORE-R17 2026-10-27: carry an R14/R16 rebuild kit (head_core_r14_rebuild.sh OUT dir) from its GRT checkpoint to a
# routed, ECO'd, sign-off-checked and LEC-checked core, per mode at every stage (R16/R17 binding).
#   head_r17_route_chain.sh KIT GOLD [MEM_GB=48] [CPUS=16]          (run ON the kit host, e.g. through ot-run --hosts)
# KIT  = rebuild dir (config.mk with the R16 per-mode block, run/results/asap7/<nick>/base/4_cts.odb [+ 5_1_grt.odb]).
# GOLD = LEC gold kit (config.mk, rtl/, macros/, lec.py) for head_post_route_eco.sh.
# Steps:
#  1 GRT: if KIT has no 5_1_grt.odb (the R16 elemA GRT stopped at the owner 10-25 structural FF hold gate,
#    OT_HOLD_STRUCTURAL ws -102.82 < -100), re-run do-5_1_grt with SKIP_INCREMENTAL_REPAIR=1: global route + the PRE hook
#    (repair_design on unscaled RC, 20 % margin), NO GRT hold repair -- data hold is the post-route ECO's job (COORD
#    ruling on R15 ASK2: post-route hold step).  An existing 5_1_grt.odb (elemB: GRT HB4 repair passed the gate) is used.
#  2 read-only GRT STA TT/FF (actual_head_sta.tcl) for the record.
#  3 route: constraint.sdc as 5_1_grt.sdc -> do-5_2_route fill 5_route finish abstract (per-mode patched container).
#  4 head_post_route_eco.sh (R17 per-mode ECO: RCX repair_design + TT setup + FF HB4 hold; the structural gate runs on
#    the RCX view first) -> signoff.py tt,ff -> routed LEC.  Out: KIT.eco (never reused).
# Log: KIT/r17_chain.log, lines R17C_*.
set -uo pipefail
KIT=$(realpath "$1"); GOLD=$(realpath "$2"); MEM=${3:-48}; CPUS=${4:-16}
HERE=$(cd "$(dirname "$0")" && pwd)
IMAGE=${OT_ORFS_IMAGE:-openroad/orfs:asap7lock}
exec >> "$KIT/r17_chain.log" 2>&1
NICK=$(sed -n 's/^export DESIGN_NICKNAME = //p' "$KIT/config.mk" | tail -1)
B=$KIT/run/results/asap7/$NICK/base
echo "R17C start $(date -Is) host $(hostname) kit $KIT nick $NICK gold $GOLD"
grep -q '^export OT_HOLD_MM = 1' "$KIT/config.mk" && grep -q 'OT_MM_FF_SDC = /work/vclk_ff.sdc' "$KIT/config.mk" \
  || { echo "R17C FAIL kit is not per-mode (R16 block missing)"; exit 2; }
python3 -I "$HERE/head_eco_modes.py" "$KIT" --check --ff-bound-ps 202.5 | grep -q '^HEAD_ECO_MODES ok' \
  || { echo "R17C FAIL kit binding check"; python3 -I "$HERE/head_eco_modes.py" "$KIT" --check; exit 2; }
test -s "$B/4_cts.odb" || { echo "R17C FAIL no 4_cts.odb"; exit 2; }
cp "$HERE/../orfs_hold_mm.py" "$HERE/../orfs_hold_mm.tcl" "$KIT/"
MMP="python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl > /work/orfs_hold_mm.\$\$.log 2>&1 || { cat /work/orfs_hold_mm.\$\$.log; exit 4; };"
DK() { docker run --rm --name "hd-r17-$NICK-$$-$1" --memory="${MEM}g" --memory-swap="${MEM}g" --cpus="$CPUS" -v "$KIT":/work \
  -e CPUS="$CPUS" -w /OpenROAD-flow-scripts/flow "$IMAGE" bash -lc "set -euo pipefail; source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; $MMP $2"; }
M="make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=\$CPUS"
if [ ! -s "$B/5_1_grt.odb" ]; then
  grep -q 'OT_HOLD_STRUCTURAL stage=grt' "$KIT/r14_grt.log" 2>/dev/null && echo "R17C prior GRT: $(grep -h 'OT_HOLD_STRUCTURAL stage=grt' "$KIT/r14_grt.log" | head -1)"
  DK grt "$M do-5_1_grt SKIP_INCREMENTAL_REPAIR=1" > "$KIT/r17_grt.log" 2>&1; rc=$?
  echo "R17C grt (no GRT hold repair) rc=$rc $(date -Is)"
  grep -h 'HD_GRT_DRV\|GRT-0303\|overflow' "$KIT/r17_grt.log" | tail -n 6
  [ $rc = 0 ] || exit 3
else
  echo "R17C grt: existing 5_1_grt.odb $(stat -c %y "$B/5_1_grt.odb") used"
fi
DK sta "for C in TT FF; do OT_HEAD_NICK=$NICK OT_CORNER=\$C openroad -threads 4 -exit /work/actual_head_sta.tcl > /work/r17_sta_\$C.log 2>&1; done"
grep -h ACTUAL_HEAD_STA "$KIT"/r17_sta_*.log
docker run --rm -v "$KIT":/work "$IMAGE" chown -R "$(id -u):$(id -g)" /work >/dev/null 2>&1
cp --remove-destination "$KIT/constraint.sdc" "$B/5_1_grt.sdc"
DK route "$M do-5_2_route do-5_3_fillcell do-5_route do-5_route.sdc && $M do-finish && $M do-generate_abstract" > "$KIT/r17_route.log" 2>&1; rc=$?
docker run --rm -v "$KIT":/work "$IMAGE" chown -R "$(id -u):$(id -g)" /work >/dev/null 2>&1
echo "R17C route rc=$rc $(date -Is)"; [ $rc = 0 ] || exit 3
test -s "$B/6_final.spef" || { echo "R17C FAIL no 6_final.spef after finish"; exit 3; }
bash "$HERE/head_post_route_eco.sh" "$KIT" "$KIT.eco" "$GOLD" "$MEM" "$CPUS"; erc=$?
echo "R17C eco chain rc=$erc $(date -Is)"
grep -h '^HEAD_ECO_\|^SIGNOFF\|OT_HOLD_STRUCTURAL' "$KIT.eco/eco_chain.log" 2>/dev/null | tail -n 25
echo "R17C done $(date -Is)"
