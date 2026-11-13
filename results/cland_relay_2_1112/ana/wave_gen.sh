#!/bin/bash
# CLAND-RELAY-2 private proof gen, wave-faithful: kit_rtl export (wave code, token compare recorded) + gen.py phys --kit-rtl
set -euo pipefail
TYPE=$1; W=$2
B=/srv/opentallas-scratch2/claude/cland-relay-2
SRC=$B/wt
PREP=/srv/opentallas-scratch2/claude/kit-ops-1/head_rp18c/prep
cd $SRC
mkdir -p $W
python3 -I $B/wave_export.py $SRC $PREP/source_plan.json $W/rtl $TYPE
export OT_PLACE_MAX_FANOUT=64 OT_IO_HOLD=sender_min OT_GEN_M8_GRANT=1 OT_FLOW_TAG=flow-20261109-fm-head
python3 tools/die_plan/gen.py phys $PREP/source_plan.json --out $W/gen --types $TYPE --rtl-root $SRC \
  --kit-rtl "$TYPE=$W/rtl/kit_rtl.f" --clock-landing $PREP/source_sidecar.json --hold-ff-margin 0 2>&1 | tee $W/gen.log
git -C $SRC rev-parse HEAD > $W/src_sha
