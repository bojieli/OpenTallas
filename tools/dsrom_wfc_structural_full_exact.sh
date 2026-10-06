#!/usr/bin/env bash
# Full changed controller only, pinned source, Kant18GiB/four-worker admission.
# Golden, default-off and structural opt-in run on the same full shape.
# Functional gate needs no physical caller-clock or parent-slot admission.
set -euo pipefail
output=${1:?new immutable output root required}
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
test ! -e "$output"
mkdir -p "$output"
run_case() {
    mode=$1; shift
    mkdir -p "$output/$mode"
    verilator --binary --timing -Wno-fatal -j 4 --top-module tb_wfc_structural_full \
      --Mdir "$output/$mode/obj" "$@" \
      "$repo/rtl/rom/wavefront/ot_rom_pkg_ctrl_wf.sv" \
      "$repo/rtl/rom/wavefront/ot_rom_pkg_ctrl_wfc.sv" \
      "$repo/rtl/test/dsrom_wavefront/tb_wfc_structural_full.sv" \
      > "$output/$mode/build.log" 2>&1
    "$output/$mode/obj/Vtb_wfc_structural_full" > "$output/$mode/run.log" 2>&1
    cat "$output/$mode/run.log"
    grep -q 'STRUCTURAL_FULL PASS' "$output/$mode/run.log"
}
# Entire 866-context/866-user namespace; fresh changed-source cases only.
run_case stg866 -GSOURCE=0 -GMAXU=866 -GUSERS=866 -GSEED=13 \
  -GNJOBS=20000 -GXWORDS=46 -GRXWORDS=41
run_case src866 -GSOURCE=1 -GMAXU=866 -GUSERS=866 -GSEED=11 \
  -GCLAT=6 -GPDLY=40 -GXWORDS=41 -GRXWORDS=41
mkdir -p "$output/warm866"
iverilog -g2012 -s tb_wfc_structural_warm_full -o "$output/warm866/warm.vvp" \
  "$repo/rtl/test/dsrom_wavefront/tb_wfc_structural_warm_full.sv" \
  "$repo/rtl/rom/wavefront/context/ot_dsrom_wfc_parent_cut.sv" \
  "$repo/rtl/rom/wavefront/context/ot_dsrom_wfc_router_cut.sv" \
  "$repo/rtl/rom/wavefront/ot_rom_pkg_ctrl_wfc.sv" \
  "$repo/rtl/rom/ot_rom_fabric_router.sv" >"$output/warm866/build.log" 2>&1
vvp "$output/warm866/warm.vvp" >"$output/warm866/run.log" 2>&1
cat "$output/warm866/run.log"
grep -q 'STRUCTURAL_WARM_FULL MAXU866 user865 PASS' "$output/warm866/run.log"
printf 'PASS_FULL_CHANGED_CONTROLLER_ONLY\n' > "$output/verdict"
