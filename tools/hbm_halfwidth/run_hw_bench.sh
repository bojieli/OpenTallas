#!/bin/bash
# HBM-HALFWIDTH-1 bench matrix (iverilog -g2012): 15 real lane configs (W, cycles-1 stations from tok_verify_rows_halfwidth.tsv),
# GARB 0/1, HW=0 wire check, and negative controls.  Exit 1 on any unexpected result.
set -u
D=$(cd "$(dirname "$0")" && pwd); RTLD=${RTLD:-$D/../../rtl/hbm_accel/generic/transport}; O=${OUT:-/tmp/hw_bench.$$}; mkdir -p "$O"; bad=0
G=${GEAR:-$D/../../rtl/common/ot_bus_gear.sv}
run() { # name expect params...
  local n=$1 e=$2; shift 2; local P=""; for p in "$@"; do P="$P -Ptb_hw_lane.$p"; done
  iverilog -g2012 -o "$O/$n.vvp" $P "$G" "$RTLD/ot_hbm_hw_lane.sv" "$D/tb_hw_lane.sv" || { echo "$n COMPILE-FAIL"; bad=1; return; }
  local r; r=$(vvp -n "$O/$n.vvp" | grep RESULT); echo "$n expect=$e :: $r"
  case "$e:$r" in PASS:*"RESULT PASS"*|FAIL:*"RESULT FAIL"*) ;; *) bad=1;; esac
}
SEED=11
while IFS=$'\t' read -r lane path w beats pw cb ca wcb wca; do
  [ "$lane" = lane ] && continue
  SEED=$((SEED+7)); g=$((SEED%2))
  run "L${lane#L}_w${w}_b2" PASS W=$w H=$((ca-1)) GARB=$g SEED=$SEED NCYC=${NCYC:-6000}
  run "L${lane#L}_w${w}_b4" PASS W=$w H=$((ca-1)) BEATS=4 GARB=$g SEED=$SEED NCYC=${NCYC:-6000}
done < "$D/tok_verify_rows_halfwidth.tsv"
run odd_w_h0        PASS W=65  H=0 GARB=1 SEED=3
run guard_on_clean  PASS W=97  H=4 GARB=1 GUARD=1 SEED=5
run odd_w_b4_h1    PASS W=67 H=1 BEATS=4 GARB=1 SEED=9
run hw0_wire        PASS W=64  H=3 HW=0
run hw0_wire_h0     PASS W=33  H=0 HW=0
# negative controls (BEATS 2 and 4)
run b4_mut_order      FAIL W=64 H=3 BEATS=4 MUTT=1
run b4_mut_drop_beat  FAIL W=64 H=3 BEATS=4 MUTR=5
run b4_mut_held_valid FAIL W=64 H=3 BEATS=4 MUTR=6
run b4_viol_ctl_s123  PASS W=64 H=3 BEATS=4 BAD=1
run b4_viol_level     PASS W=64 H=3 BEATS=4 BAD=2 GUARD=1
run mut_order       FAIL W=64 H=3 MUTT=1
run mut_drop_beat   FAIL W=64 H=3 MUTR=5
run mut_held_valid  FAIL W=64 H=3 MUTR=6
run mut_hold_off    FAIL W=64 H=3 MUTR=7
run viol_ctl_slot1  PASS W=64 H=3 BAD=1
run viol_ctl_noguard FAIL W=64 H=3 BAD=1 MUTT=4
run viol_level_slot1 PASS W=64 H=3 BAD=2 GUARD=1
[ $bad = 0 ] && echo "BENCH PASS" || { echo "BENCH FAIL"; exit 1; }
