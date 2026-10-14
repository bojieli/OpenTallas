#!/usr/bin/env bash
# Link the existing HOST/board/allocator/cohort archives (no RTL rebuild) and run
# the lifecycle gate in positive and both negative-control modes. Run under ot-run.
set -euo pipefail
src=${1:?directory holding host_lifecycle_gate.cpp host_lifecycle.hpp host_owner.hpp router+drain headers}
out=${2:?fresh output directory}
c=/srv/opentallas-scratch/codex/qwen-native-host-callable-1014
host=$c/full8bb9a6c00-compiledO1/obj; board=$c/boardd4a77a6c7/obj
alloc=$c/native-host-owner-models/allocator; cohort=$c/native-host-owner-models/cohort
vroot=/home/ubuntu/.local/opentallas-tools/verilator-5.050/share/verilator/include
[[ ! -e "$out" ]]; mkdir -p "$out"
arch=("$host/Vqkd_host_token_service__ALL.a" "$board/Vqkd_host_board_port_fixture__ALL.a" "$alloc/Vot_qwen_tp8_token_epoch_allocator__ALL.a" "$cohort/Vot_qwen_tp8_token_cohort__ALL.a")
sha256sum "$src"/host_lifecycle_gate.cpp "$src"/host_lifecycle.hpp "$src"/host_owner.hpp "$src"/qkd_host_board_router_fixture.hpp "$src"/qkd_host_drain_8bb.hpp "${arch[@]}" > "$out/inputs.sha256"
g++ -std=c++20 -O1 -pthread -I"$src" -I"$host" -I"$board" -I"$alloc" -I"$cohort" -I"$vroot" -I"$vroot/vltstd" \
 "$src/host_lifecycle_gate.cpp" "${arch[@]}" "$vroot/verilated.cpp" "$vroot/verilated_threads.cpp" -o "$out/lifecycle" > "$out/link.log" 2>&1
sha256sum "$out/lifecycle" >> "$out/inputs.sha256"
status=0
for mode in positive strict stale; do
 set +e; "$out/lifecycle" "$out/$mode" "$mode" > "$out/$mode.log" 2>&1; rc=$?; set -e
 echo "$mode rc=$rc $(tail -1 "$out/$mode.log")"
 if [[ $mode == positive && $rc != 0 ]]; then status=1; fi
 if [[ $mode != positive && $rc == 0 ]]; then status=1; fi
done
exit $status
