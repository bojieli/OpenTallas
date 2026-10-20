#!/bin/bash
set -eu
E=$PWD/results/rtl/kv_ectl_h15_1020
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
for mut in 0 1;do
 "$V" --binary --timing --x-initial unique --x-assign unique -j 2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -GMUT=$mut --top-module tb_reset_publication_v2 -Mdir "$E/obj_resetpub_v2_$mut" "$E/tb_reset_publication_v2.sv" rtl/qwen_sys/static_kv_20261014/ot_ectl_h15_reset_publish32.sv rtl/lib/ot_rst_relay.sv rtl/lib/ot_rst_relay_bounded32.sv rtl/hdc/nearhbm/ot_qwen_nearhbm_attn_stack_h.sv > "$E/build_resetpub_v2_$mut.log" 2>&1
 set +e
 "$E/obj_resetpub_v2_$mut/Vtb_reset_publication_v2" +verilator+seed+19 +verilator+rand+reset+2 > "$E/run_resetpub_v2_$mut.log" 2>&1
 rc=$?
 set -e
 if [ "$mut" = 0 ];then test "$rc" = 0;grep RESET_PUBLICATION_PASS "$E/run_resetpub_v2_$mut.log"
 else test "$rc" -ne 0;grep RESET_PUBLICATION_STAGE_MISMATCH "$E/run_resetpub_v2_$mut.log";fi
done
