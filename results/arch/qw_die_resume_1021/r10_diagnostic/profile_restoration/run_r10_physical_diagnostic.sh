#!/bin/bash
set -euo pipefail
S=$(cd "$(dirname "$0")" && pwd)
export PYTHONDONTWRITEBYTECODE=1
export OT_SAVED_CASE_PHYSICAL_DIAGNOSTIC=1 OT_SAVED_CASE_ROOT="$S"
export OT_SAVED_CASE_MANIFEST="$S/saved_case_diagnostic_manifest.json"
export OT_BIND_FWD_CLASSES=0 OT_SPLIT_FWD_CLASSES=0 OT_SPLIT_FWD_CLASS_PACK=0
export OT_BIND_VIEW_SELECT="$S/physical_view_select.json"
export OT_SPLIT_PHY_TALL=1 OT_SPLIT_PHY_NFACE=1 OT_SPLIT_UCIE_PHY_CLK=1
python3 "$S/physical_profile_guard.py" "$S" > "$S/physical_profile_guard.json"
export OT_QWEN_D2D_IMAGE=rtl/qwen_sys/d2d_static_20261015/d2d_cal_image_mu_ew595_r16.svh
export OT_SPLIT_RST_REGION_LAND=1 OT_SPLIT_FWD_RST_SYNC=1 OT_RST_REP_VIEW=closed
export OT_PORT_BIND_STRAPS="$S/src/results/arch/qwen_split_compute_1014/q_slice_1017/straps_dv2f18mu.json"
export OT_PORT_BIND_UCIE_VIEW=physical/qwen_missing_phy/nface_tall_1017/ot_qfd_ucie_x64_phy
# Match the original admitted physical recipe. Every PG failure remains FAIL.
export OT_PDN_RELAY_GRIDS=1 OT_ASSUMED_PHY_PG_ACCESS=1 OT_CHAIN_DIAGNOSTIC=1
exec bash "$S/src/tools/qwen_split/chain_after_build.sh" dv2f21g5r10bfp_diag_profile1536
