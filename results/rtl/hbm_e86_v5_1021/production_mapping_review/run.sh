#!/usr/bin/env bash
# REVIEW ONLY: ROOT authorization required before any invocation.
# The caller stages immutable committed source into $PWD/src, overlaying ONLY
# published_overlay paths with their exact PACKET hashes. Two RTL hashes unchanged.
set -euo pipefail
R=$(pwd)
P="$R/src/results/rtl/hbm_e86_v5_1021/production_mapping_review"
mkdir -p "$R/production_mapping"
cp "$P/config.mk" "$P/constraint.sdc" "$P/image_libs.json" "$P/inside.sh" "$R/production_mapping/"
sha256sum "$P"/published_overlay/physical/common_flow/ot_keep_regs.tcl "$R/src"/physical/common_flow/ot_keep_regs.tcl > "$R/production_mapping/hook_before.sha256"
docker run --rm -v "$R/src:/src:ro" -v "$R/production_mapping:/work" -w /OpenROAD-flow-scripts/flow sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 bash /work/inside.sh
