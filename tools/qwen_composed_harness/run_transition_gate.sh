#!/usr/bin/env bash
set -euo pipefail
cd "${COMPOSED_STAGE:?actual fresh candidate stage}"
mkdir -p out tmp
export TMPDIR="$PWD/tmp"
front=/srv/opentallas-scratch/codex/native-services-frontend-1014/library-v1/obj
sector=/srv/opentallas-scratch/codex/native-services-frontend-1014/sector-library-v1/obj
pc=/srv/opentallas-scratch/codex/qwen-native-hbm-pc-provider-1014/library_v2/obj
vroot=/home/ubuntu/.local/opentallas-tools/verilator-5.050/share/verilator
for input_path in src/* kernel/*; do if [[ -f "$input_path" ]]; then sha256sum "$input_path"; fi; done > out/inputs.sha256
sha256sum "$front/Vot_qwen_tp8_native_services_frontend__ALL.a" \
 "$sector/Vot_qwen_tp8_kv_sector_adapter__ALL.a" "$pc/Vqwen_native_hbm_pc_provider__ALL.a" \
 vectors/* vectors-layer1/* >> out/inputs.sha256
c++ -std=c++17 -O1 -pthread -I"$front" -I"$sector" -I"$pc" -Ikernel -Isrc \
 -I"$vroot/include" -I"$vroot/include/vltstd" src/composed.cpp \
 "$front/Vot_qwen_tp8_native_services_frontend__ALL.a" "$sector/Vot_qwen_tp8_kv_sector_adapter__ALL.a" \
 "$pc/Vqwen_native_hbm_pc_provider__ALL.a" kernel/Vot_qwen_tp8_attention_service__ALL.a \
 kernel/sim_hdc_v41x_fastfp_dpi.o kernel/sim_nhb_fp_lat_dpi.o \
 "$vroot/include/verilated.cpp" "$vroot/include/verilated_threads.cpp" "$vroot/include/verilated_dpi.cpp" \
 -o out/composed > out/link.log 2>&1
sha256sum out/composed > out/executable.sha256
out/composed vectors transition vectors-layer1 > out/transition.log 2>&1
set +e
out/composed vectors transition_data_mut vectors-layer1 > out/transition_data_mut.log 2>&1
data_status=$?
out/composed vectors transition_ack_mut vectors-layer1 > out/transition_ack_mut.log 2>&1
ack_status=$?
set -e
printf '%s %s\n' "$data_status" "$ack_status" > out/mutant_status.txt
[[ "$data_status" == 1 ]]
[[ "$ack_status" == 2 ]]
grep -q 'mismatch' out/transition_data_mut.log
grep -q 'FAIL composed RTL fault stage 6 frame 1' out/transition_ack_mut.log
cat out/transition.log out/transition_data_mut.log out/transition_ack_mut.log
