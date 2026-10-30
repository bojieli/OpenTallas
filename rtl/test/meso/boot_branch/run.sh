#!/bin/bash
set -eu
W=/srv/opentallas-scratch2/claude/wt/codex-collft-0336
B=/srv/opentallas-scratch2/claude/codex-collft-0336/boot_proof
mkdir -p "$B"
cd "$W"
iverilog -g2012 -s tb_boot_branch -o "$B/normal.vvp" rtl/common/ot_meso_fifo.sv rtl/common/ot_dp_clk_landing.sv rtl/common/ot_dp_clk_landing_ca.sv rtl/test/meso/boot_branch/tb_boot_branch.sv
for P in 83 209 417 711; do
 for D in 0 1; do
  for E in 0 1; do
   vvp "$B/normal.vvp" +PHASE="$P" +PAD="$D" +EFALL="$E"
  done
 done
done
for M in BOOT_MUTANT_K OT_BOOT_BRANCH_MUTANT_RESET OT_BOOT_BRANCH_MUTANT_STAGE; do
 iverilog -g2012 -s tb_boot_branch -D"$M" -o "$B/$M.vvp" rtl/common/ot_meso_fifo.sv rtl/common/ot_dp_clk_landing.sv rtl/common/ot_dp_clk_landing_ca.sv rtl/test/meso/boot_branch/tb_boot_branch.sv
 if vvp "$B/$M.vvp" +PHASE=711 +PAD=0 +EFALL=1 >"$B/$M.log" 2>&1; then
  echo "MUTANT_SURVIVED $M";exit 1
 fi
 echo "MUTANT_CAUGHT $M $(head -n 1 "$B/$M.log")"
done
