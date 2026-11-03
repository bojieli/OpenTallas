#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-pg-birth-cts-0219/cts_pg0_0253
A=$R/audit
B=$R/kit/run/results/asap7/kl_dsfd_node_LLfd_c/base/4_1_cts.odb
test -s "$B"
[ ! -e "$A/LLfd" ]
mkdir "$A/LLfd"
docker run --rm --network none --memory=4g --memory-swap=4g --cpus=2 -v "$R/kit":/work:ro -v "$A":/out -e ODB=/work/run/results/asap7/kl_dsfd_node_LLfd_c/base/4_1_cts.odb -e OUT=/out/LLfd/sites.tsv -e OT_GEOM_OUT=/out/LLfd/geom.tsv sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 bash -lc 'set -e; source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -threads 2 -exit /out/sites_audit.tcl' > "$A/LLfd/census.log" 2>&1
docker run --rm --network none --memory=4g --memory-swap=4g --cpus=1 -v "$R/kit":/work:ro -v "$A":/out -e OT_PG_AUDIT_ODB=/work/run/results/asap7/kl_dsfd_node_LLfd_c/base/4_1_cts.odb -e OT_PG_AUDIT_REPORT=/out/LLfd/native_pg.json sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 bash -lc 'set -e; source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -threads 1 -exit /out/audit_native_pg.tcl' > "$A/LLfd/pg_audit.log" 2>&1
