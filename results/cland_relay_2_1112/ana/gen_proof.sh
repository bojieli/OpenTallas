#!/bin/bash
# CLAND-RELAY-2 private proof gen: gen.py phys (HEAD-95 recipe) on rp18c prepared plan, kit-wave gen_args/env.
set -euo pipefail
TYPE=$1; OUT=$2
B=/srv/opentallas-scratch2/claude/cland-relay-2
SRC=$B/wt
PREP=/srv/opentallas-scratch2/claude/kit-ops-1/head_rp18c/prep
PD=$B/pd_rp18c
mkdir -p $PD
for f in $PREP/*; do n=$(basename $f); [ "$n" = source_plan.json ] && continue; [ -e $PD/$n ] || ln -s $f $PD/$n; done
[ -e $PD/die_plan.json ] || ln -s $PREP/source_plan.json $PD/die_plan.json
mkdir -p $OUT
cd $SRC
export OT_PLACE_MAX_FANOUT=64 OT_IO_HOLD=sender_min OT_GEN_M8_GRANT=1 OT_FLOW_TAG=flow-20261109-fm-head
python3 tools/die_plan/gen.py phys $PREP/source_plan.json --out $OUT/gen --types $TYPE --rtl-root $SRC \
  --clock-landing $PREP/source_sidecar.json --hold-ff-margin 0 2>&1 | tee $OUT/gen.log
git -C $SRC rev-parse HEAD > $OUT/src_sha
