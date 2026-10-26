#!/bin/bash
# usage: arrs.sh label spef_in_container ...  -> arr_<label>_<TT|FF>.txt
D=/srv/opentallas-scratch2/claude/infra-r5-1026/drt
while [ $# -gt 0 ]; do lab=$1; spef=$2; shift 2
 for c in TT FF; do
  docker run --rm --memory=8g -v $D:/d -v /srv/opentallas-scratch2/claude/infra-r4-1026/drt:/src:ro -e OT_ODB=/d/q52sw_drt_grt.odb -e OT_SPEF=$spef -e OT_CORNER=$c -e OT_OUT=/d/arr_${lab}_$c.txt openroad/orfs:asap7lock bash -c "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /d/arr_pins.tcl > /d/arr_${lab}_$c.log 2>&1; chown 1000:1000 /d/arr_${lab}_$c.*"
 done; done
