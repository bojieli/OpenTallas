#!/bin/bash
set -euo pipefail
cd run
python3 xpf_identity.py
s=../src
"$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" --binary --timing -Wno-fatal -j 4  --top-module tb_xpf_compact_producer_ids -Mdir xpf_id_obj  "$s/rtl/qwen_sys/dvm_20261014/ot_qfd_xpf_static_schedule.sv"  "$s/rtl/test/qwen_dv/tb_xpf_compact_producer_ids.sv" > xpf_id_build.log 2>&1
for m in original compact_duplicate clone24;do
 set +e
 xpf_id_obj/Vtb_xpf_compact_producer_ids "+RECORDS=$PWD/xpf_$m.hex" > "xpf_id_$m.log" 2>&1
 rc=$?
 set -e
 if [ "$m" = compact_duplicate ];then test "$rc" != 0;grep XPF_PRODUCER_ID_INSTALL_REJECT "xpf_id_$m.log"
 else test "$rc" = 0;grep XPF_PRODUCER_ID_INSTALL_PASS "xpf_id_$m.log";fi
done
