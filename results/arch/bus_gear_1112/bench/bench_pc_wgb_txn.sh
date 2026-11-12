#!/usr/bin/env bash
# BUS-GEAR-1: PC write-data gearbox transaction equivalence (tb_hbm_pc_wgb_txn.sv). Usage: bench_pc_wgb_txn.sh OUT [BASE_REV]
# Runs WRH 1 (h9b bench mix) and 6 (write-heavy) exact, then MUT 1 (no W_GAP) and 2 (side-band not delayed), which must FAIL;
# with BASE_REV also the default-param lockstep (tb_hbm_pc_wgb_lockstep.sv: 0 pin mismatches on any edge vs BASE).
set -uo pipefail
out=${1:?output}; mkdir -p "$out"; d=rtl/hbm_accel/loader/service_native; bad=0
src="rtl/lib/ot_rst_relay.sv rtl/model_ready_hbm_r14/ot_hbm_r14_stream_pc_strap_h9.sv $d/ot_hbm_svc_pin_skid2_h9.sv $d/ot_hbm_svc_ring_h9b.sv
 $d/ot_hbm_svc_pc_ctrl_leaf_cfg_h9b.sv rtl/common/ot_bus_gear.sv $d/ot_hbm_pc_phy_gear_rx.sv
 physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v"
run1() { local n=wrh$1_mut$2
  iverilog -g2012 -s tb -Ptb.WRH=$1 -Ptb.MUT=$2 -o "$out/$n.vvp" $src $d/tb_hbm_pc_wgb_txn.sv > "$out/$n.build.log" 2>&1 || { echo "$n BUILD FAIL" > "$out/$n.res"; return; }
  echo "$n expect=$3 :: $(vvp -n "$out/$n.vvp" 2>&1 | tee "$out/$n.log" | grep -E 'WGB_TXN (PASS|FAIL)')" > "$out/$n.res"; }
for c in "1 0 PASS" "6 0 PASS" "6 1 FAIL" "1 2 FAIL"; do run1 $c & done   # independent configs in parallel
# default-parameter lockstep: BASE's cfg + strap (renamed __orig) vs this tree's cfg at defaults, every pin every edge
base=${2:-}; if [ -n "$base" ]; then
  git show "$base:$d/ot_hbm_svc_pc_ctrl_leaf_cfg_h9b.sv" | sed -e 's/module ot_hbm_svc_pc_ctrl_leaf_cfg_h9b__fcore/&__orig/' \
    -e 's/ot_hbm_r14_stream_pc_strap_h9 #/ot_hbm_r14_stream_pc_strap_h9__orig #/' > "$out/orig_cfg.sv"
  git show "$base:rtl/model_ready_hbm_r14/ot_hbm_r14_stream_pc_strap_h9.sv" | sed 's/module ot_hbm_r14_stream_pc_strap_h9/&__orig/' > "$out/orig_strap.sv"
  iverilog -g2012 -s tb_lock -Ptb_lock.WRH=6 -Ptb_lock.MUT=2 -o "$out/lock.vvp" $src "$out/orig_strap.sv" "$out/orig_cfg.sv" \
    $d/tb_hbm_pc_wgb_lockstep.sv > "$out/lock.build.log" 2>&1 || { echo "lock BUILD FAIL"; bad=1; }
  r=$(vvp -n "$out/lock.vvp" 2>&1 | tee "$out/lock.log" | grep -E 'LOCK_TXN (PASS|FAIL)'); echo "lockstep vs $base :: $r"
  case "$r" in *"LOCK_TXN PASS"*) ;; *) bad=1;; esac
fi
wait
for c in "1 0 PASS" "6 0 PASS" "6 1 FAIL" "1 2 FAIL"; do set -- $c; r=$(cat "$out/wrh$1_mut$2.res"); echo "$r"
  case "$3:$r" in PASS:*"WGB_TXN PASS"*|FAIL:*"WGB_TXN FAIL"*) ;; *) bad=1;; esac
done
[ $bad = 0 ] && echo "PC_WGB BENCH PASS" || { echo "PC_WGB BENCH FAIL"; exit 1; }
