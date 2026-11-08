#!/bin/bash
cd /
set -euo pipefail
D=/srv/opentallas-scratch2/claude/codex-kv-types-1113/pc_pg
B=/srv/opentallas-scratch3/claude/dkv78/hhp/k4u/i1/run/results/asap7/hc_qkd_kvs_pcc_h_head_p__293_76x267_84/base
docker run --rm --name codex-kv-pc-pg-exact-1113 -v "$B:/base:ro" -v "$D:/out" openroad/orfs:asap7lock /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /out/export.tcl > "$D/export.log" 2>&1
