#!/bin/bash
set -euo pipefail
WT=${1:?fresh caller-owned worktree}
HOST=${2:?staging host}
ROOT=${3:?new immutable remote run root}
ASSET_REF=${4:-HEAD}
[ "$(git -C "$WT" rev-parse --show-toplevel)" = "$WT" ]
BASE=982c1f5494dd141baae7216fe7195806e65b32e9
HELPER=46f5246efda404c54c7925269213bc41300c5eae
ssh "$HOST" "test ! -e '$ROOT' && mkdir -p '$ROOT/src'"
git -C "$WT" archive "$BASE" rtl/hbm_accel/generic rtl/lib rtl/test/hbm_accel/generic rtl/common/landed_parent rtl/hdc rtl/proto physical/common_flow physical/qwen_die_masters physical/hbm_accel_die_views/stations/bench physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2 physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2 physical/ref_tile/hbm_su_pgrg_pair_d4g physical/ref_tile/hbm_su_pgrg_pair_d4g_fb physical/ref_tile/hbm_su_static_kind0_l4_leaf1_1015 physical/ref_tile/hbm_su_static_bank6_clock7_1015 results/rtl/hbm_pglg8_1020 tools/hbm_static/su_pgslice_rg_vl_run.sh tools/hbm_static/su_pgrg_region_gen.py | ssh "$HOST" "tar -x -C '$ROOT/src'"
git -C "$WT" archive "$HELPER" tools physical/common_flow physical/qwen_die_masters physical/hbm_accel_die_views/stations/bench | ssh "$HOST" "tar -x -C '$ROOT/src'"
git -C "$WT" archive "$BASE" tools/hbm_static/su_pgrg_region_gen.py tools/hbm_static/su_pgslice_rg_vl_run.sh | ssh "$HOST" "tar -x -C '$ROOT/src'"
git -C "$WT" archive "$ASSET_REF" tools/hbm_static/pg982_qualification | ssh "$HOST" "tar -x -C '$ROOT/src'"
printf '%s\n' "$BASE" | ssh "$HOST" "cat > '$ROOT/src/SOURCE_COMMIT'"
printf '%s\n' "$HELPER" | ssh "$HOST" "cat > '$ROOT/src/HELPER_COMMIT'"
ssh "$HOST" "cd '$ROOT/src' && sha256sum rtl/hbm_accel/generic/adapters/static_su/top/ot_hbm_su_pgrg_pair.sv tools/hbm_static/su_pgrg_region_gen.py tools/hbm_static/pg982_qualification/* > '$ROOT/input.sha256'"
printf 'Staged only; no heavy job invoked: %s:%s\n' "$HOST" "$ROOT"
