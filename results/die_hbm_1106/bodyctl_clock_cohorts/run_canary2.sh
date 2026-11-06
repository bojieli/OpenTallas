#!/bin/bash
set -euo pipefail
kit=/srv/opentallas-scratch2/claude/codex-bodyctl-rcp1-production5-bm/kits/ot_hfd_coll_q3_body_ctl_cf148fd0f3e3-vA_rcp_rr
out=/srv/opentallas-scratch2/claude/codex-bodyctl-clock-canary2
mkdir -p "$out"
docker run --rm --cpus=1 --memory=4g -v "$kit:/kit:ro" -v "$out:/out" openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /out/query_canary.tcl'
