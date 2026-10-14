#!/usr/bin/env bash
set -euo pipefail
cd /srv/opentallas-scratch/codex/qwen-composed-harness-1014
mkdir -p out tmp
export TMPDIR="$PWD/tmp"
front=/srv/opentallas-scratch/codex/native-services-frontend-1014/library-v1/obj
sector=/srv/opentallas-scratch/codex/native-services-frontend-1014/sector-library-v1/obj
pc=/srv/opentallas-scratch/codex/qwen-native-hbm-pc-provider-1014/library_v2/obj
vroot=/home/ubuntu/.local/opentallas-tools/verilator-5.050/share/verilator
sha256sum src/* kernel/* "$front/Vot_qwen_tp8_native_services_frontend__ALL.a" "$sector/Vot_qwen_tp8_kv_sector_adapter__ALL.a" "$pc/Vqwen_native_hbm_pc_provider__ALL.a" vectors/* > out/inputs.sha256
c++ -std=c++17 -O1 -pthread -I"$front" -I"$sector" -I"$pc" -Ikernel -Isrc -I"$vroot/include" -I"$vroot/include/vltstd" \
 src/composed.cpp "$front/Vot_qwen_tp8_native_services_frontend__ALL.a" \
 "$sector/Vot_qwen_tp8_kv_sector_adapter__ALL.a" "$pc/Vqwen_native_hbm_pc_provider__ALL.a" \
 kernel/Vot_qwen_tp8_attention_service__ALL.a kernel/sim_hdc_v41x_fastfp_dpi.o kernel/sim_nhb_fp_lat_dpi.o \
 "$vroot/include/verilated.cpp" "$vroot/include/verilated_threads.cpp" "$vroot/include/verilated_dpi.cpp" \
 -o out/composed > out/link.log 2>&1
out/composed vectors > out/positive.log 2>&1
out/composed vectors stalls > out/stalls.log 2>&1
set +e
out/composed vectors data_mut > out/data_mut.log 2>&1
data_status=$?
out/composed vectors ack_mut > out/ack_mut.log 2>&1
ack_status=$?
set -e
[[ "$data_status" == 1 ]]
[[ "$ack_status" == 2 ]]
grep -q "mismatch" out/data_mut.log
grep -q "FAIL composed RTL fault" out/ack_mut.log
cat out/positive.log out/stalls.log out/data_mut.log out/ack_mut.log
