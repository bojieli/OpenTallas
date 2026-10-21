#!/bin/bash
set -euo pipefail
python3 - <<'BIND'
import json,hashlib
from pathlib import Path
for name,sha in json.load(open('readset_sha256.json')).items():
 assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==sha,name
BIND
iverilog -V > iverilog.version 2>&1
iverilog -g2012 -DOT_MEM_NO_INIT -s tb -o component.vvp qkd_hr_ingest_shell__proof_core.v ot_pin_regs_wrapper.v qkd_hr_ingest_cdc_shell.sv ot_reset_sync.sv ot_host_die_cdc_sram.sv ot_link_afifo.sv ot_sram_1r1w2c_32x546_m1_p192_mir.v tb_quiescent_system_reset.sv vendor_and2.v > build.log 2>&1
for mode in 0 1 2 3;do
 set +e
 vvp component.vvp +MODE=$mode > mode$mode.log 2>&1
 rc=$?
 set -e
 printf 'mode=%s rc=%s\n' "$mode" "$rc" >> receipt.log
 if [ "$mode" = 0 ];then
  [ "$rc" = 0 ];grep -q QUIESCENT_SYSTEM_RESET_COMPONENT_PASS mode$mode.log
 else
  [ "$rc" != 0 ];grep -q EXPECTED_CONTRACT_VIOLATION mode$mode.log
 fi
done
echo COMPONENT_BOUNDED_POSITIVE_AND_THREE_CAUSALS_PASS
