#!/usr/bin/env bash
# BUS-GEAR-1: yosys sequential equivalence, default parameters, origin/main form (gold) vs the WGB/W_GAP form (gate)
# for ot_hbm_r14_stream_pc_strap_h9 and ot_hbm_svc_pc_ctrl_leaf_cfg_h9b__fcore. Usage (in a worktree): eqv_default.sh BASE OUT
set -euo pipefail
base=${1:?base rev}; out=${2:?out}; mkdir -p "$out"; d=rtl/hbm_accel/loader/service_native
if [ "$base" != "-" ]; then git show "$base:rtl/model_ready_hbm_r14/ot_hbm_r14_stream_pc_strap_h9.sv" > "$out/gold_strap.sv"
  git show "$base:$d/ot_hbm_svc_pc_ctrl_leaf_cfg_h9b.sv" > "$out/gold_cfg.sv"; fi   # "-": gold_*.sv already in OUT
lib="rtl/lib/ot_rst_relay.sv $d/ot_hbm_svc_pin_skid2_h9.sv $d/ot_hbm_svc_ring_h9b.sv"
mac=physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
for top in ot_hbm_r14_stream_pc_strap_h9 ot_hbm_svc_pc_ctrl_leaf_cfg_h9b__fcore; do
  if [ $top = ot_hbm_r14_stream_pc_strap_h9 ]; then g="$out/gold_strap.sv"; n=rtl/model_ready_hbm_r14/ot_hbm_r14_stream_pc_strap_h9.sv; gx=""; nx="";
  else g="$out/gold_cfg.sv"; n=$d/ot_hbm_svc_pc_ctrl_leaf_cfg_h9b.sv; gx="$out/gold_strap.sv"; nx="rtl/model_ready_hbm_r14/ot_hbm_r14_stream_pc_strap_h9.sv rtl/common/ot_bus_gear.sv"; fi
  cat > "$out/$top.ys" <<YS
read_verilog -lib $mac
read_verilog -sv -DSYNTHESIS $lib $gx $g
hierarchy -top $top
proc; flatten; opt_clean; memory_map; opt -fast
rename $top gold
design -stash gold
read_verilog -lib $mac
read_verilog -sv -DSYNTHESIS $lib $nx $n
hierarchy -top $top
proc; flatten; opt_clean; memory_map; opt -fast
rename $top gate
design -stash gate
design -copy-from gold -as gold gold
design -copy-from gate -as gate gate
equiv_make gold gate equiv
hierarchy -top equiv
async2sync
equiv_simple -seq 5
equiv_induct -seq 5
equiv_status -assert
YS
  yosys -q -l "$out/$top.log" "$out/$top.ys" > /dev/null 2>&1 && echo "$top EQUIV PASS" || { echo "$top EQUIV FAIL"; grep -E 'unproven|Found' "$out/$top.log" | head -5; }
done
