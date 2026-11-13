#!/bin/bash
set -eu
R=/srv/opentallas-scratch2/claude/wt/hard-s81-dsdv-1
D=/srv/opentallas-scratch2/claude/hard-s81-dsdv-1/wcc_alias
mkdir -p "$D"
cp "$R/rtl/common/ot_meso_fifo.sv" "$R/rtl/common/ot_dp_clk_landing.sv" "$R/rtl/test/meso/wcc_group/tb_wcc_group.sv" "$D/"
cp /srv/opentallas-scratch2/claude/hard-s81-dsdv-1/wcc_group2/ot_ref_meso_fifo.sv /srv/opentallas-scratch2/claude/hard-s81-dsdv-1/wcc_group2/ot_ref_dp_clk_landing.sv "$D/"
cd "$D"
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
for edge in 0 1; do
  verilator --binary --timing -j 4 -Wno-fatal --top-module tb_wcc_group -DOT_MESO_WCC_GROUP16 -GWNEG="$edge" --Mdir "obj_$edge" \
    tb_wcc_group.sv ot_dp_clk_landing.sv ot_meso_fifo.sv ot_ref_dp_clk_landing.sv ot_ref_meso_fifo.sv > "build_$edge.log" 2>&1
  for phase in 0 83 208 416 625 750; do
    "obj_$edge/Vtb_wcc_group" +PHASE="$phase" > "run_${edge}_${phase}.log" 2>&1
    grep 'WCC_GROUP ' "run_${edge}_${phase}.log"
  done
done
echo WCC_ALIAS_BENCH_PASS
