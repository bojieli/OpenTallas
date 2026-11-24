#!/bin/bash
# usage: sta_ep_census.sh KITDIR ODB_REL SDC_REL OUTDIR TAG   (kit mounted read-only; run via ot-run)
# Uses KITDIR/setRC_rcx.tcl when present. Writes OUTDIR/TAG.rcx.sum(+.hold); then: sta_ep_census.py OUTDIR/TAG.rcx.sum
set -euo pipefail
K=$1 O=$2 S=$3 D=$4 T=$5
mkdir -p "$D"; cp "$(dirname "$(readlink -f "$0")")/sta_ep_census.tcl" "$D/"
exec docker run --rm --cpus=4 --memory=60g -v "$K:/work:ro" -v "$D:/out" --workdir /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc '
 source /OpenROAD-flow-scripts/env.sh >/dev/null
 LIBS=$(make DESIGN_CONFIG=/work/config.mk WORK_HOME=/tmp/wh FLOW_VARIANT=base print-LIB_FILES 2>/dev/null | sed -n "s/^LIB_FILES: *//p")
 SETRC=$(make DESIGN_CONFIG=/work/config.mk WORK_HOME=/tmp/wh FLOW_VARIANT=base print-SET_RC_TCL 2>/dev/null | sed -n "s/^SET_RC_TCL: *//p")
 [ -f /work/setRC_rcx.tcl ] && SETRC=/work/setRC_rcx.tcl
 echo "LIBS $(echo $LIBS | wc -w) SETRC $SETRC"
 export LIBS SETRC ODB=/work/$1 SDC=/work/$2 OUT=/out/$3.rcx.sum
 openroad -exit -no_init /out/sta_ep_census.tcl 2>&1 | tail -20
' bash "$O" "$S" "$T"
