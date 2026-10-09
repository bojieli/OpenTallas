#!/bin/bash
# run_cg.sh <src_root> <out_dir> [cfg dir: cg | cg_k24]  (drive-1443: half-rate gater fix variants of h2 fixedpins)
set -eu
S=$1; O=$2; V=${3:-cg}
mkdir -p "$O"
set +e
docker run --rm -v "$S":/src:ro -v "$O":/work openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; cd /OpenROAD-flow-scripts/flow; make DESIGN_CONFIG=/src/physical/hbm_ha2_fixedpins_20261007/$V/config.mk WORK_HOME=/work NUM_CORES=16 finish; rc=\$?; chmod -R a+rwX /work; exit \$rc" > "$O/run.log" 2>&1
rc=$?
printf '%s\n' "$rc" > "$O/terminal.exit"
grep -h "OT_CG_PUSHDOWN total\|OT_HA2_GCLK" "$O"/logs/asap7/*/base/4_1_cts.log >> "$O/run.log" 2>/dev/null
exit "$rc"
