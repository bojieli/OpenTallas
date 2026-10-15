#!/usr/bin/env bash
set -euo pipefail
out=${1:?output directory}; mkdir -p "$out"
src=(rtl/dsrom_sys/s81_static_net/test/tb_r2l_groups64.sv rtl/dsrom_sys/s81_static_net/ot_s81_r2l_groups64.sv rtl/dsrom_sys/s81_static_net/ot_s81_static_ratio_cross.sv rtl/dsrom_sys/s81_static_net/gen/dsfd_r2l_vr_512x1__hcol.sv)
for phase in 0 1 3 5 7 9 11; do
  iverilog -g2012 -s tb_r2l_groups64 -Ptb_r2l_groups64.PHASE="$phase" -o "$out/p$phase.vvp" "${src[@]}"
  vvp "$out/p$phase.vvp" > "$out/p$phase.log"
  grep -q 'R2L_GROUPS_PASS checks=398' "$out/p$phase.log"
done
iverilog -g2012 -s tb_r2l_groups64 -Ptb_r2l_groups64.MUT=1 -o "$out/mapping_mutant.vvp" "${src[@]}"
if vvp "$out/mapping_mutant.vvp" > "$out/mapping_mutant.log" 2>&1; then echo 'MUTANT DID NOT FAIL'; exit 1; fi
grep -q 'R2L_GROUPS_FAIL checks=.*errors=[1-9]' "$out/mapping_mutant.log"
echo 'R2L_GROUPS_GATE_PASS phases7 epochs28 exact_each_edge zero_added_edges mutant_rejected'
