#!/usr/bin/env bash
# Run in the pinned remote source checkout after Kant's unchanged admission.
# Four compiler workers; no wall-time, file, memory or CPU-time deadline.
set -euo pipefail
output=${1:?new immutable output root required}
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
test ! -e "$output"
mkdir -p "$output"
iverilog -g2012 -s tb_wfc_decoded_read -o "$output/bank.vvp" \
  "$repo/rtl/test/dsrom_wavefront/tb_wfc_decoded_read.sv" \
  "$repo/rtl/rom/wavefront/ot_rom_pkg_ctrl_wfc.sv" >"$output/bank_build.log" 2>&1
vvp "$output/bank.vvp" >"$output/bank_run.log" 2>&1
bash "$repo/tools/dsrom_wfc_reset_reference_recipe.sh" "$output/src866" \
  -DOT_WFC_DECODED_READ=1 -GSOURCE=1 -GLOCKSTEP=0 -GMAXU=866 \
  -GUSERS=866 -GSEED=11 -GCLAT=6 -GPDLY=40 -GXWORDS=41 -GRXWORDS=41
# No SOURCE0 successor logic was changed. This full-shape lockstep checks
# that the new opt-in parameter does not affect its existing stage path.
bash "$repo/tools/dsrom_wfc_reset_reference_recipe.sh" "$output/stg866" \
  -DOT_WFC_DECODED_READ=1 -GSOURCE=0 -GMAXU=866 -GUSERS=866 \
  -GSEED=13 -GNJOBS=20000 -GXWORDS=46 -GRXWORDS=41
printf 'PASS_FULL_SHAPE_EXACT_ONLY\n' >"$output/verdict"
