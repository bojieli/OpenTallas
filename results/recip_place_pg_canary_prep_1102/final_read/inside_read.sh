#!/bin/bash
set -euo pipefail
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
cd /OpenROAD-flow-scripts/flow
python3 -I /work/orfs_hold_mm.py scripts > /case/READ_NORMAL_MM_PATCH.log
make -f Makefile -f /case/audit_only.mk DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=1 ot_private_saved_pg_audit
for label in SYNTH FP PLACE; do
 INVENTORY_LABEL="$label" openroad -no_init -threads 1 -exit -python /case/inventory_db.py
done
