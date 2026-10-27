#!/bin/bash
set -euo pipefail
S=/srv/opentallas-scratch2/claude/codex-hbm-cores-0815/ep_anchor_actual
I=/srv/opentallas-scratch2/claude/codex-hbm-ep-0825/kits_compact/hfd_ep_static_2bb0ef5ca18b-q6c3/run/results/asap7/hbc_hfd_ep_static/base
D=/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad
docker run --rm -v "$I:/input:ro" -v "$S:/out" -e OT_GEOM_OUT=/out/actual_v3.tsv openroad/orfs:asap7lock "$D" -exit /out/apply_v3.tcl
