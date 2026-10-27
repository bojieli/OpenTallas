#!/bin/bash
set -euo pipefail
# placement uses the r5 spec only for the FIRM entry root (ot_h_fixed = ot_ms_root at the same entry); CTS uses mscts_spec_r7.tcl
K=$(cd "$(dirname "$0")" && pwd)
rc=0; docker run --rm --name btr7-pl-$(basename $K)-$$ --cpus=8 --memory=28g --memory-swap=28g -v "$K":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 OT_MSCTS_SPEC=/work/mscts_spec_r5.tcl place' > "$K/place_r7.log" 2>&1 || rc=$?
docker run --rm -v "$K":/work openroad/orfs:asap7lock chown -R $(id -u):$(id -g) /work/run
exit $rc
