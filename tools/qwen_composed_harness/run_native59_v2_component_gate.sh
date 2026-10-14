#!/usr/bin/env bash
# Distinct actual composition; inputs remain explicit checkpoint Q/SU fixtures.
set -euo pipefail
[[ ! -e out ]];mkdir -p out tmp
export TMPDIR="$PWD/tmp"
front=/srv/opentallas-scratch/codex/native-services-front59-1014/v2/library/obj
sector=/srv/opentallas-scratch/codex/native-services-frontend-1014/sector-library-v1/obj
pc=/srv/opentallas-scratch/codex/qwen-native-hbm-pc-provider-1014/library_v2/obj
kernel=/srv/opentallas-scratch/codex/qwen-composed-harness-f460-1014/kernel
vroot=/home/ubuntu/.local/opentallas-tools/verilator-5.050/share/verilator
sha256sum src/* vectors/* vectors-layer1/* "$front/Vot_qwen_tp8_native_services_frontend_native59__ALL.a" "$sector/Vot_qwen_tp8_kv_sector_adapter__ALL.a" "$pc/Vqwen_native_hbm_pc_provider__ALL.a" "$kernel/Vot_qwen_tp8_attention_service__ALL.a" "$kernel/sim_hdc_v41x_fastfp_dpi.o" "$kernel/sim_nhb_fp_lat_dpi.o" > out/inputs.sha256
c++ -std=c++17 -O1 -pthread -I"$front" -I"$sector" -I"$pc" -I"$kernel" -Isrc -I"$vroot/include" -I"$vroot/include/vltstd" src/composed_native59_v2.cpp "$front/Vot_qwen_tp8_native_services_frontend_native59__ALL.a" "$sector/Vot_qwen_tp8_kv_sector_adapter__ALL.a" "$pc/Vqwen_native_hbm_pc_provider__ALL.a" "$kernel/Vot_qwen_tp8_attention_service__ALL.a" "$kernel/sim_hdc_v41x_fastfp_dpi.o" "$kernel/sim_nhb_fp_lat_dpi.o" "$vroot/include/verilated.cpp" "$vroot/include/verilated_threads.cpp" "$vroot/include/verilated_dpi.cpp" -o out/composed_native59_v2 > out/link.log 2>&1
sha256sum out/composed_native59_v2 > out/executable.sha256
out/composed_native59_v2 vectors positive > out/positive.log 2>&1
out/composed_native59_v2 vectors stalls > out/stalls.log 2>&1
out/composed_native59_v2 vectors transition vectors-layer1 > out/transition.log 2>&1
set +e
out/composed_native59_v2 vectors transition_data_mut vectors-layer1 > out/transition_data_mut.log 2>&1
data_status=$?
out/composed_native59_v2 vectors transition_ack_mut vectors-layer1 > out/transition_ack_mut.log 2>&1
ack_status=$?
out/composed_native59_v2 vectors transition_q_replay vectors-layer1 > out/transition_q_replay.log 2>&1
replay_status=$?
set -e
printf '%s %s %s\n' "$data_status" "$ack_status" "$replay_status" > out/mutant_status.txt
[[ "$data_status" == 1 && "$ack_status" == 2 && "$replay_status" == 2 ]]
rg -q 'mismatch' out/transition_data_mut.log
rg -q 'FAIL composed RTL fault stage 6 frame 1' out/transition_ack_mut.log
rg -q 'REPLAY_ACTUAL_OLD_Q_RESPONSE stage1_to_stage2 sameepoch0 .*layer1_ATTN_commits=0' out/transition_q_replay.log
rg -q 'FAIL composed RTL fault stage 7 frame 1' out/transition_q_replay.log
cat out/positive.log out/stalls.log out/transition.log out/transition_data_mut.log out/transition_ack_mut.log out/transition_q_replay.log

for mode in transition_vm_ack_replay transition_vm_token_mut transition_vm_position_mut transition_vm_segment_mut; do
 set +e
 out/composed_native59_v2 vectors "$mode" vectors-layer1 > "out/$mode.log" 2>&1
 status=$?
 set -e
 printf '%s %s\n' "$mode" "$status" >> out/vm_ack_mutant_status.txt
 [[ "$status" == 2 ]]
 rg -q 'INJECT_ACTUAL_VM_ACK .*bridge_count_before=0 layer1_actual_VM_writes=[1-9][0-9]*' "out/$mode.log"
 rg -q 'REJECT_ACTUAL_VM_ACK bridge_count_after=0' "out/$mode.log"
 rg -q 'FAIL composed RTL fault stage 7 frame 1' "out/$mode.log"
 cat "out/$mode.log"
done
