#!/bin/bash
set -eu
R=/srv/opentallas-scratch2/claude/wt/hard-s81-dsdv-1
D=/srv/opentallas-scratch2/claude/hard-s81-dsdv-1/wcc_group2
mkdir -p "$D"
cp "$R/rtl/common/ot_meso_fifo.sv" "$D/ot_meso_fifo.sv"
cp "$R/rtl/common/ot_dp_clk_landing.sv" "$D/ot_dp_clk_landing.sv"
cp "$R/rtl/test/meso/wcc_group/tb_wcc_group.sv" "$D/"
git -C "$R" show 21bde8b3af:rtl/common/ot_meso_fifo.sv | sed 's/ot_meso_/ot_ref_meso_/g' > "$D/ot_ref_meso_fifo.sv"
sed 's/ot_dp_clk_landing/ot_ref_dp_clk_landing/g; s/ot_meso_/ot_ref_meso_/g' "$R/rtl/common/ot_dp_clk_landing.sv" > "$D/ot_ref_dp_clk_landing.sv"
cd "$D"
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
for mode in off group mutant; do
  defs=()
  if [ "$mode" != off ]; then defs+=(-DOT_MESO_WCC_GROUP=16); fi
  if [ "$mode" = mutant ]; then defs+=(-DOT_MESO_WCC_GROUP_MUTANT); fi
  for edge in 0 1; do
    name=${mode}_${edge}
    verilator --binary --timing -j 4 -Wno-fatal --top-module tb_wcc_group \
      "${defs[@]}" -GWNEG="$edge" --Mdir "obj_$name" \
      tb_wcc_group.sv ot_dp_clk_landing.sv ot_meso_fifo.sv ot_ref_dp_clk_landing.sv ot_ref_meso_fifo.sv > "build_$name.log" 2>&1
    for phase in 0 83 208 416 625 750; do
      run_name=${name}_${phase}
      if "obj_$name/Vtb_wcc_group" +PHASE="$phase" > "run_$run_name.log" 2>&1; then
        [ "$mode" != mutant ] || { echo "MUTANT_SURVIVED $run_name"; exit 1; }
      else
        [ "$mode" = mutant ] || { cat "run_$run_name.log"; exit 1; }
      fi
      echo "CASE $run_name EXPECTED_RESULT"; grep -E "WCC_GROUP |LOCKSTEP_FAIL" "run_$run_name.log"
    done
  done
done
echo WCC_GROUP_BENCH_PASS
