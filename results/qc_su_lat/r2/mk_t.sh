#!/bin/bash
# mk_t.sh R2KIT TKIT SPEC : variant T (binary tree) on the SAME R2 3_place (island placement), CTS+GRT only
set -euo pipefail
S=$1; D=$2; R=$(dirname $(readlink -f $0))
rsync -a --exclude 'run/results/*/*/base/4_*' --exclude 'run/results/*/*/base/5_*' --exclude 'run/logs' --exclude 'lat_*' --exclude 'taps.txt' --exclude 'trunk_*' --exclude 'r2_*' --exclude 'geo*' $S/ $D/
cd $D; cp $3 mscts_spec.tcl; cp $R/mscts_tree.tcl cf/mscts_tree.tcl
P=$(grep '^export PRE_CTS_TCL' config.mk | tail -n1 | awk '{print $4}' | sed 's#/work/##')
grep -q mscts_tree $P || sed -i 's#^ot_ms_build#source /work/cf/mscts_tree.tcl\not_ms_build#' $P
grep -n 'mscts_tree\|^ot_ms_build' $P
printf '# QC-SU-LAT-R2 variant T %s: binary structured tree (cf/mscts_tree.tcl), same island placement as %s\n' "$(date '+%F %R %Z')" "$S" >> config.mk
echo "T kit from $S $(date -Is)" > image.txt
