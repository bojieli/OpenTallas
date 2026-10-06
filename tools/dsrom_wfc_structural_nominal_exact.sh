#!/usr/bin/env bash
# Necessary nominal SOURCE0 correction only; completed SOURCE1 is reused.
set -euo pipefail
output=${1:?new output root}; retained=${2:?completed R2 root}
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
test "$(cat "$retained.control/terminal.exit")" = 0
grep -q 'STRUCTURAL_FULL PASS' "$retained/src866/run.log"
test ! -e "$output"
mkdir -p "$output/stg866" "$output/source_lifecycle"
sha256sum "$retained/src866/run.log" "$retained/src866/obj/Vtb_wfc_structural_full__ALL.a" > "$output/source1_reused.sha256"
verilator --binary --timing -Wno-fatal -j 4 --top-module tb_wfc_structural_full \
 --Mdir "$output/stg866/obj" -GSOURCE=0 -GINJECT_ILLEGAL=0 -GMAXU=866 -GUSERS=866 \
 -GSEED=13 -GNJOBS=20000 -GXWORDS=46 -GRXWORDS=41 \
 "$repo/rtl/rom/wavefront/ot_rom_pkg_ctrl_wf.sv" "$repo/rtl/rom/wavefront/ot_rom_pkg_ctrl_wfc.sv" \
 "$repo/rtl/test/dsrom_wavefront/tb_wfc_structural_full.sv" > "$output/stg866/build.log" 2>&1
(cd "$output/stg866" && ./obj/Vtb_wfc_structural_full) > "$output/stg866/run.log" 2>&1
grep -q 'STRUCTURAL_FULL PASS' "$output/stg866/run.log"
for lane in 0 1 2; do grep -q "NOMINAL_GOLD lane=$lane accepted=20000 VM=820000 launches=20000 forwarded=20000 flits=940000.*fault=0" "$output/stg866/run.log"; done
iverilog -g2012 -s tb_wfc_source_lifecycle -o "$output/source_lifecycle/lifecycle.vvp" \
 "$repo/rtl/rom/wavefront/ot_rom_pkg_ctrl_wfc.sv" "$repo/rtl/test/dsrom_wavefront/tb_wfc_source_lifecycle.sv" > "$output/source_lifecycle/build.log" 2>&1
vvp "$output/source_lifecycle/lifecycle.vvp" > "$output/source_lifecycle/run.log" 2>&1
grep -q 'SOURCE1_LIFECYCLE_ALL PASS' "$output/source_lifecycle/run.log"
sha256sum -c "$output/source1_reused.sha256" > "$output/source1_reused_check.log"
printf 'PASS_NOMINAL_SOURCE0_AND_RETAINED_SOURCE1_FUNCTIONAL_ONLY\n' > "$output/verdict"
