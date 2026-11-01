#!/bin/bash
set -euo pipefail
V=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator
for hb in 0 1;do
 $V --binary --timing --top-module tb_s81sl_xrt_qrel_eq -GHB=$hb --build-jobs 2 -Wno-fatal -Wno-WIDTH -Wno-PINMISSING -Wno-TIMESCALEMOD --output-split 5000 --Mdir obj_hb$hb ot_rst_relay.sv ot_s81sl_xrt.sv ref_xrt.sv tb_exact_xrt.sv >hb${hb}_build.log 2>&1
 obj_hb$hb/Vtb_s81sl_xrt_qrel_eq >hb${hb}.log 2>&1
 grep -q '^PASS' hb${hb}.log
 tail -4 hb${hb}.log
done
printf 'HB0_RC=0\nHB1_RC=0\n' >status.txt
cat status.txt
