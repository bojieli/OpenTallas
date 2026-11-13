#!/bin/bash
# usage: slewnets.sh KIT OUTDIR  -- TT routed slew-violator nets with pin/wire cap (kit signoff TT session head + tail)
set -euo pipefail
K=$1; O=$2; mkdir -p $O
S=$K/signoff/tt
n=$(grep -n '^read_sdc /sdc/golden.sdc' $S/session.tcl | head -1 | cut -d: -f1)
head -n $n $S/session.tcl | sed 's#ot_lib_load TT /out/libraries.json#ot_lib_load TT /out/libraries_cr2.json#' > $O/session.tcl
cat /srv/opentallas-scratch2/claude/cland-relay-2/slewnets_tail.tcl >> $O/session.tcl
docker run --rm -v $K/run/results/asap7/$(ls $K/run/results/asap7)/base:/base:ro -v $S/sdcdir:/sdc:ro -v $O:/out -v $K:/work:ro \
  -v $K/config.mk:/work/config.mk:ro openroad/orfs:asap7lock /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /out/session.tcl > $O/session.log 2>&1
tail -3 $O/session.log
