#!/bin/bash
set -euo pipefail
WT=${1:?caller-owned WT}; HOST=${2:?staging host}; ROOT=${3:?fresh immutable root}; SOURCE=${4:?source commit}
HELPER=$(git -C "$WT" rev-parse "${WBK1340_HELPER_COMMIT:-99eff96d0ee86f973604b0190e0cebd01388cc2f}^{commit}")
[ "$(git -C "$WT" rev-parse --show-toplevel)" = "$WT" ]
ssh "$HOST" "test ! -e '$ROOT' && mkdir -p '$ROOT/src'"
git -C "$WT" archive "$HELPER" tools physical/common_flow physical/qwen_die_masters | ssh "$HOST" "tar -x -C '$ROOT/src'"
git -C "$WT" archive "$SOURCE" rtl/hbm_accel/loader/service_native rtl/hbm_accel/service rtl/lib rtl/link rtl/model_ready_hbm_r14 physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2 physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2 physical/asap7_stdcell_native_models/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib tools/hbm_static/wbk_native_1340 results/rtl/hbm_wbk8_1020 results/rtl/hbm_wbk_native_1340 | ssh "$HOST" "tar -x -C '$ROOT/src'"
printf '%s\n' "$SOURCE" | ssh "$HOST" "cat > '$ROOT/src/SOURCE_COMMIT'"
printf '%s\n' "$HELPER" | ssh "$HOST" "cat > '$ROOT/src/HELPER_COMMIT'"
ssh "$HOST" "cd '$ROOT/src' && sha256sum rtl/link/ot_link_afifo.sv rtl/hbm_accel/loader/service_native/ot_hbm_svc_wb_kq8.sv physical/asap7_stdcell_native_models/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib tools/hbm_static/wbk_native_1340/* > '$ROOT/input.sha256'"
printf 'STAGED_ONLY %s:%s source%s helper%s\n' "$HOST" "$ROOT" "$SOURCE" "$HELPER"
