#!/bin/bash
set -uo pipefail
K=$(cd "$(dirname "$0")" && pwd)
P=$K/run/results/asap7/kr_dsdv_eng_rr_e_r0c0/base/3_place.odb
S=$K/run/results/asap7/kr_dsdv_eng_rr_e_r0c0/base/3_place.sdc
sha256sum "$P" "$S" > "$K/cts_source_before.sha256"
docker run --rm --cpus=8 --memory=48g --memory-swap=48g -v "$K":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 do-4_1_cts do-4_cts; rc=$?; chown -R 1000:1000 /work; exit $rc' > "$K/cts_side17.log" 2>&1
rc=$?
sha256sum "$P" "$S" > "$K/cts_source_after.sha256"
cmp -s "$K/cts_source_before.sha256" "$K/cts_source_after.sha256" || { echo PLACEMENT_OR_SDC_SOURCE_CHANGED >> "$K/cts_side17.log";rc=9; }
echo "$rc" > "$K/cts_side17.exit"
exit "$rc"
