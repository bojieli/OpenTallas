#!/bin/bash
# usage: holdviol.sh KIT OUTDIR -- full kit FF sign-off session + hold-violator list
set -euo pipefail
K=$1; O=$2; mkdir -p $O; S=$K/signoff/ff
sed '/^so_timing STD$/r /srv/opentallas-scratch2/claude/cland-relay-2/hold_tail.tcl' $S/session.tcl > $O/session.tcl
docker run --rm -v $K/run/results/asap7/$(ls $K/run/results/asap7)/base:/base:ro -v $S/sdcdir:/sdc:ro -v $O:/out -v $K:/work:ro \
  -v $K/config.mk:/work/config.mk:ro openroad/orfs:asap7lock /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /out/session.tcl > $O/session.log 2>&1
grep "CR2" $O/session.log
