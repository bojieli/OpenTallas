#!/usr/bin/env bash
set -euo pipefail
base=/srv/opentallas-scratch/codex/qwen-full-layer-sequence-1014
front=/srv/opentallas-scratch/codex/native-services-front59-1014/v2/library/obj
sector=/srv/opentallas-scratch/codex/native-services-frontend-1014/sector-library-v1/obj
pc=/srv/opentallas-scratch/codex/qwen-native-hbm-pc-provider-1014/library_v2/obj
vroot=/home/ubuntu/.local/opentallas-tools/verilator-5.050/share/verilator
mkdir -p out
sha256sum src/layer_models.hpp src/full_layer_helpers_loop.hpp src/helper_full_loop_syntax.cpp src/native59_helpers.hpp src/host_owner.hpp src/qkd_host_board_router_fixture.hpp host_headers/*.h cohort_headers/*.h > out/inputs.sha256
c++ -std=c++20 -fsyntax-only -Isrc -Ihost_headers -Icohort_headers -I"$base/generated_lv6_headers" -I"$base/allocator_v5_0/library/obj" -I"$base/native59_helper/obj" -I"$front" -I"$sector" -I"$pc" -I/srv/opentallas-scratch/codex/qwen-composed-harness-f460-1014/kernel -I"$vroot/include" -I"$vroot/include/vltstd" src/helper_full_loop_syntax.cpp > out/syntax.log 2>&1
printf '%s\n' PASS_ACTUAL_HELPER_CORE_HOST_DRIVER_SYNTAX_ONLY_HOST_GATE_PENDING
