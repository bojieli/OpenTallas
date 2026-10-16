#!/bin/bash
set -eu
source_dir=/srv/opentallas-scratch/claude/ref_gate/qfd_ucie_gearbox_r10-20261016-030510/src
docker run --rm -w /OpenROAD-flow-scripts/flow -v "$source_dir":/src:ro -v "$PWD/orfs":/work openroad/orfs:latest bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 /src/tools/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts >/dev/null; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base SKIP_CTS_REPAIR_TIMING=1 cts' > cts_no_repair.log 2>&1
