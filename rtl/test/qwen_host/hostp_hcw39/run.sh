#!/bin/bash
# KV-P2-RTL 10-23: run from the repository root (Verilator 5.050).  MUT 0 PASS; MUT 1 (no bypass) and MUT 2 (unmasked
# 182-bit station) must FAIL.  OUT (default ./hostp_hcw39_out) holds the objects and logs.
set -eu
D=rtl/test/qwen_host/hostp_hcw39; O=${1:-hostp_hcw39_out}; mkdir -p "$O"; O=$(realpath "$O")
python3 $D/check_source.py
export PATH="$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH"
verilator --version
for m in 0 1 2; do
 verilator --binary --timing -j 4 -Wno-fatal --top-module tb_hostp_local_program -GMUT=$m -Mdir "$O/obj$m" $D/tb_hostp_local_program.sv rtl/qwen_sys/host_20261013/qkd_host_program_loader_target.sv rtl/qwen_sys/host_20261013/qkd_host_hc_station.sv rtl/physical/ot_qwen_host_ctl.sv rtl/qwen_sys/system_20261008/ot_qfd_pkgctl.sv physical/asap7_memory_macros/ot_sram_1rw_256x64_m4_r2c2/ot_sram_1rw_256x64_m4_r2c2.v >"$O/build$m.log" 2>&1 || { tail -40 "$O/build$m.log"; exit 2; }
 set +e; "$O/obj$m/Vtb_hostp_local_program" >"$O/m$m.log" 2>&1; rc=$?; set -e
 grep -v '^- ' "$O/m$m.log"; echo "MUT=$m RC=$rc"
 if [ "$m" = 0 ]; then [ "$rc" = 0 ]; grep -q 'HOSTP_LOCAL PASS' "$O/m$m.log"; else [ "$rc" != 0 ]; grep -Eq 'actual HC|HOSTP_LOCAL FAIL|authorized footer' "$O/m$m.log"; fi
done
echo 'HOSTP_HCW39_SUITE PASS production1024pw8dw twoCausalMutants'
