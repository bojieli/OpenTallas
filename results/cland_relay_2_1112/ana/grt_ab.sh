#!/bin/bash
# usage: grt_ab.sh KIT OUTDIR MAXL RA NETLIST
set -euo pipefail
K=$1; O=$2; MAXL=$3; RA=$4; NL=$5; mkdir -p $O; cp $NL $O/netlist.txt
S=$K/signoff/tt
n=$(grep -n '^read_db /base/6_final.odb' $S/session.tcl | head -1 | cut -d: -f1)
head -n $((n-1)) $S/session.tcl | sed 's#ot_lib_load TT /out/libraries.json#ot_lib_load TT /out/libraries_cr2.json#' > $O/session.tcl
cat >> $O/session.tcl <<EOT
read_db /base/5_1_grt.odb
read_sdc /base/5_1_grt.sdc
EOT
cat /srv/opentallas-scratch2/claude/cland-relay-2/grt_ab_tail.tcl >> $O/session.tcl
D=$K/run/results/asap7/$(ls $K/run/results/asap7)/base
docker run --rm -e CR2_MAXL=$MAXL -e CR2_RA=$RA -v $D:/base:ro -v $O:/out -v $K:/work:ro \
  openroad/orfs:asap7lock /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -threads 8 -exit /out/session.tcl > $O/session.log 2>&1
grep "CR2" $O/session.log
