#!/bin/bash
# PHY RE-FORM bench + mutants.  usage: run.sh EVENT_PLAN BOUND_RTL_DIR CELLS_DIR WORK
#   EVENT_PLAN    plan after phy_pi_reform.py; BOUND_RTL_DIR the current bind rtl/ (OLD wrappers + bind_cells.sv)
#   CELLS_DIR     kit landing cells (ot_dp_clk_landing*.sv, ot_meso_fifo.sv, ot_reset_sync.sv)
# Expect: kv3_phy/kv3_phy_v1 none -> PASS (host_eq_probe 0); every mutant -> FAIL.
set -u
H=$(cd "$(dirname "$0")" && pwd)
PLAN=$1; BR=$2; CD=$3; W=$4
mkdir -p "$W"
rc=0
for row in "kv3_phy kv3_phy_part none" "kv3_phy kv3_phy_part d3_depth2" "kv3_phy kv3_phy_part relay_on_bout" \
           "kv3_phy_v1 kv3_phy_v1_part none" "kv3_phy_v1 kv3_phy_v1_part d3_depth2"; do
  set -- $row; tn=$1; mod=$2; mut=$3
  for st in early late; do
    d=$W/${tn}_${mut}_${st}; rm -rf "$d"; mkdir -p "$d"
    m=(); [ "$mut" = none ] || m=(--mutant "$mut")
    python3 -I "$H/make_rtl.py" "$PLAN" "$tn" "$BR/$mod.sv" "$d" "${m[@]}" > "$d/make.log" 2>&1 || { echo "$tn $mut $st MAKE_FAIL"; tail -3 "$d/make.log"; rc=1; continue; }
    s=(); [ "$st" = late ] && s=(--late-start)
    python3 -I "$H/gen_tb.py" "$BR/$mod.sv" "$mod" 3 "$d/tb.sv" "${s[@]}"
    iverilog -g2012 -o "$d/sim" "$d/tb.sv" "$BR/$mod.sv" "$d/$mod.sv" "$H/phy_stub.sv" "$BR/bind_cells.sv" \
      "$CD/ot_dp_clk_landing.sv" "$CD/ot_dp_clk_landing_ca.sv" "$CD/ot_meso_fifo.sv" "$CD/ot_reset_sync.sv" > "$d/iverilog.log" 2>&1 \
      || { echo "$tn $mut $st COMPILE_FAIL"; head -5 "$d/iverilog.log"; rc=1; continue; }
    vvp -n "$d/sim" > "$d/sim.log" 2>&1
    res=$(grep '^BENCH' "$d/sim.log")
    exp=PASS; [ "$mut" = none ] || exp=FAIL
    got=$(echo "$res" | awk '{print $2}')
    ok=OK; [ "$got" = "$exp" ] || { ok=UNEXPECTED; rc=1; }
    echo "$tn mutant=$mut start=$st expect=$exp -> $res [$ok]"
  done
done
exit $rc
