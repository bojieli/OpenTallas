#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/../.."
ROOT=$PWD
IMG=openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29
mkdir -p map_v2 evidence_map_v2
cp tests/pg_canonical_coupon_1019/synth_config.mk map_v2/config.mk
docker image inspect "$IMG" >evidence_map_v2/image.json
docker run --rm "$IMG" bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; sha256sum "$(command -v openroad)" "$(command -v yosys)"; openroad -version; yosys -V; find /OpenROAD-flow-scripts/flow/platforms/asap7 /OpenROAD-flow-scripts/flow/scripts -type f -print0 | sort -z | xargs -0 sha256sum' >evidence_map_v2/tool_platform_orfs.sha256 2>&1
/usr/bin/time -v docker run --rm -v "$ROOT:/src:ro" -v "$ROOT/map_v2:/work" -w /OpenROAD-flow-scripts/flow "$IMG" bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base synth' >evidence_map_v2/synthesis.log 2>evidence_map_v2/synthesis.time
