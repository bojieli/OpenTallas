#!/bin/bash
# Run from repository root on the admitted fleet.
set -eu
python3 results/rtl/kv_hostp_local_program_1023/check_source.py
export PATH="$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH"
verilator --version
for m in 0 1 2; do
 verilator --binary --timing -j 4 -Wno-fatal --top-module tb_hostp_local_program -GMUT=$m -Mdir obj$m results/rtl/kv_hostp_local_program_1023/tb_hostp_local_program.sv rtl/qwen_sys/host_20261013/qkd_host_program_loader_target.sv rtl/qwen_sys/host_20261013/qkd_host_hc_station.sv rtl/physical/ot_qwen_host_ctl.sv rtl/qwen_sys/system_20261008/ot_qfd_pkgctl.sv physical/asap7_memory_macros/ot_sram_1rw_256x64_m4_r2c2/ot_sram_1rw_256x64_m4_r2c2.v >build$m.log 2>&1 || { tail -40 build$m.log; exit 2; }
 set +e
 ./obj$m/Vtb_hostp_local_program >m$m.log 2>&1
 rc=$?
 set -e
 cat m$m.log
 echo "MUT=$m RC=$rc"
 if [ "$m" = 0 ]; then [ "$rc" = 0 ]; grep -q 'HOSTP_LOCAL PASS' m$m.log; else [ "$rc" != 0 ]; grep -Eq 'actual HC|HOSTP_LOCAL FAIL|authorized footer' m$m.log; fi
done
echo 'HOSTP_LOCAL_SUITE PASS production1024pw8dw twoCausalMutants'
