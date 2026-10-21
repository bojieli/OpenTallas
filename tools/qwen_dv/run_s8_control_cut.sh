#!/usr/bin/env bash
set -euo pipefail
out=$1
mkdir -p "$out"
inputs=(rtl/test/qwen_dv/s8/control_cut/{rp1_reference,fdn_arf1_reference,reset_dependencies,masked_production_helpers,guard_cut,masked_cut}.sv rtl/qwen_dv/s5/s8/qfd_dv_s8_rp1.sv rtl/qwen_dv/s5/s8/qfd_dv_s8_fdn_arf1.sv rtl/common/landed_parent/ot_pl_land_n32.sv)
sha256sum "${inputs[@]}" > "$out/sources.sha256"
iverilog -V > "$out/version.txt" 2>&1
iverilog -g2012 -s tb_s8_control_cut -o "$out/cut.vvp" "${inputs[@]}" > "$out/build.log" 2>&1
sha256sum "$out/cut.vvp" > "$out/binary.sha256"
timeout 60 vvp "$out/cut.vvp" > "$out/primary.log" 2>&1
cat "$out/primary.log"
grep -q S8_CONTROL_CUT_PASS "$out/primary.log"
