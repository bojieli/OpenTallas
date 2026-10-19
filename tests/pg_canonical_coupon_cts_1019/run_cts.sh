#!/bin/bash
set -euo pipefail
MODE=${1:?default or strict}
case "$MODE" in default|strict) ;; *) exit 2;; esac
ROOT=$(pwd)
OUT=$ROOT/output/$MODE
mkdir -p "$OUT"
export OPENTALLAS_ORFS_IMAGE=openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29
export OT_ORFS_CORNER_OVERRIDE=TC OT_ORFS_NUM_CORES=4
export OT_CTS_FIX_HOOKS='physical/common_flow/cg_pushdown.tcl physical/common_flow/clk_net_protect.tcl physical/common_flow/link_budget_hook.tcl'
export HM=0.03 OT_ROUTE_HOLD_CORNERS=mm
export OT_MM_FF_SDC=physical/ref_tile/pg_xor16_cts_${MODE}_1019/signoff.sdc
export SRC=$ROOT
docker image inspect "$OPENTALLAS_ORFS_IMAGE" > "$OUT/image.json"
docker run --rm "$OPENTALLAS_ORFS_IMAGE" bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; sha256sum "$(command -v openroad)" "$(command -v yosys)"; find /OpenROAD-flow-scripts/flow/platforms/asap7 /OpenROAD-flow-scripts/flow/scripts -type f -print0 | sort -z | xargs -0 sha256sum' > "$OUT/tool_platform_orfs.sha256"
/usr/bin/time -v bash tools/ref_tile/ref_route.sh physical/ref_tile/pg_xor16_cts_${MODE}_1019/kit.env canonical_cts "$OUT/routes" cts > "$OUT/driver.log" 2> "$OUT/driver.time"
