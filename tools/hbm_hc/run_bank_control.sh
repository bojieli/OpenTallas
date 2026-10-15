#!/usr/bin/env bash
set -euo pipefail
out=${1:?output directory};mkdir -p "$out"
python3 - "$out" <<'PY'
import pathlib,sys
p=pathlib.Path('rtl/hdc/v41x/ot_hdc_v41x_hcp.sv').read_text();stage=p[p.index('module ot_hdc_v41x_hcp_stage #('):p.index('module ot_hdc_v41x_hcp_lanes #(')]
o=pathlib.Path(sys.argv[1]);(o/'reference.sv').write_text('`timescale 1ns/1ps\n'+stage)
p=pathlib.Path('rtl/hbm_accel/generic/peers/static_hc/ot_hgi_hc_bank_control_static.sv').read_text();assert 'assign o_v=cv[8]' in p
(o/'mutant.sv').write_text(p.replace('assign o_v=cv[8]','assign o_v=cv[7]'))
PY
for m in 0 1;do
 shell=rtl/hbm_accel/generic/peers/static_hc/ot_hgi_hc_bank_control_static.sv
 [[ $m == 0 ]] || shell="$out/mutant.sv"
 iverilog -g2012 -s tb_hgi_hc_bank_control_static -o "$out/m$m.vvp" "$out/reference.sv" "$shell" rtl/hbm_accel/generic/peers/static_hc/ot_hgi_hc_bank_memory_shared_static.sv rtl/test/tb_hgi_hc_bank_control_static.sv physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v >"$out/m$m.compile.log" 2>&1
 set +e
 vvp "$out/m$m.vvp" >"$out/m$m.log" 2>&1;rc=$?
 set -e
 if [[ $m == 0 ]];then [[ $rc == 0 ]];grep 'BANK_CONTROL PASS' "$out/m$m.log";else [[ $rc != 0 ]];grep 'BANK_CONTROL.*mismatch' "$out/m$m.log";fi
done
