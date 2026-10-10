#!/bin/bash
# CLAUDE WFC src route: ORFS route, then signoff STA.  /src = pinned source /srv/opentallas-scratch/claude/closure-loop/mtp-wfc-src-tokpipe-9f7a7f35e-tc/src
set -u
W=/srv/opentallas-scratch/claude/closure-loop/mtp-wfc-src-tokpipe-9f7a7f35e-tc/route; S=/srv/opentallas-scratch/claude/closure-loop/mtp-wfc-src-tokpipe-9f7a7f35e-tc/src; IMG=openroad/orfs:latest
cd $W; echo "start $(date -Is)" > $W/status
/srv/opentallas-scratch/admit.sh 64 -- docker run --rm --name claude-wfc-mtp-wfc-src-tokpipe-9f7a7f35e-tc-wfc_src_route -v $S:/src:ro -v $W:/work \
  -w /OpenROAD-flow-scripts/flow $IMG bash -lc "trap 'chmod -R a+rwX /work >/dev/null 2>&1 || true' EXIT; \
  source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work \
  FLOW_VARIANT=base NUM_CORES=12 ${WFC_TARGET:-finish}" > $W/flow.log 2>&1
echo "flow_rc=$?" >> $W/status
if [[ "${WFC_TARGET:-finish}" != "finish" ]]; then exit 0; fi
cd $S && python3 tools/dsrom_wfc_tokpipe_physical.py sta --inst src --case $W --macros > $W/sta.log 2>&1
echo "sta_rc=$?" >> $W/status
python3 tools/dsrom_wfc_tokpipe_physical.py check --inst src --case $W > $W/check.log 2>&1
echo "end $(date -Is)" >> $W/status
