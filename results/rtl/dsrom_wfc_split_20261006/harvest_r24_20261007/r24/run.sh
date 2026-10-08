#!/bin/bash
# CLAUDE WFC src r22 (HM 32, out_* pad 60 + SS repair_design): r13 case up to GRT + FF/region hold repair on 5_1_grt.odb, then ORFS 5_2 route .. finish, then driver sign-off
set -u
R=/srv/opentallas-scratch/claude/dsrom-wfc-split; W=$R/r24/src_u55; S=$R/src-region; B=$W/results/asap7/wfc_src_src_u55/base
echo "start $(date -Is)" > $R/r24/status
docker run --rm --name claude-wfc-r24eco -v $B:/in -v $B:/out -v $R/r24/eco:/eco:ro -v $S:/src:ro -e OT_HOLD_MARGIN=32 -e OT_SETUP_MARGIN=25 \
  openroad/orfs:latest bash -lc "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /eco/grt_eco.tcl; chmod -R a+rwX /out" > $R/r24/eco.log 2>&1
grep -q "OT_ECO done" $R/r24/eco.log || { echo "eco_failed" >> $R/r24/status; echo "end $(date -Is)" >> $R/r24/status; exit 1; }
echo "eco_ok" >> $R/r24/status
docker run --rm --name claude-wfc-r24drv -v $B:/out -v $R/r24/eco:/eco:ro -v $S:/src:ro openroad/orfs:latest bash -lc "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /eco/grt_drv.tcl; chmod -R a+rwX /out" > $R/r24/drv.log 2>&1
grep -q "OT_DRV done" $R/r24/drv.log || { echo "drv_failed" >> $R/r24/status; echo "end $(date -Is)" >> $R/r24/status; exit 1; }
echo "drv_ok" >> $R/r24/status
docker run --rm --name claude-wfc-r24 -v $S:/src:ro -v $W:/work -w /OpenROAD-flow-scripts/flow openroad/orfs:latest bash -lc "trap 'chmod -R a+rwX /work >/dev/null 2>&1 || true' EXIT; \
  source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base NUM_CORES=12 finish" > $W/flow.log 2>&1
echo "flow_rc=$?" >> $R/r24/status
cd $S && python3 tools/dsrom_wfc_split_physical.py sta --case $W --macros > $W/sta.log 2>&1
echo "sta_rc=$?" >> $R/r24/status
python3 tools/dsrom_wfc_split_physical.py check --case $W > $W/check.log 2>&1
echo "end $(date -Is)" >> $R/r24/status
