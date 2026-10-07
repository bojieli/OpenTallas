#!/bin/bash
# q-element closure post-processing for a routed run R (usage: close_qz.sh R WTCLOSE):
# (1) abstract from 6_final.odb (tools/dsrom_q_abstract.tcl), (2) single-instance pin access
# (physical/abi3/dsrom_q_pin_access.tcl), (3) S81 die-level pin access with OT_S81_Q_LEF (tools/dsrom_s81_fulldie.py real).
set -u
R=$1; WTC=$2
T=/srv/opentallas-scratch/claude/dsrom-qtclose; J=$T/jobs/$R; C=$T/close/$R; mkdir -p $C/pa $C/die
B=$(ls -d $J/work/orfs/results/asap7/*/base | head -1)
docker run --rm -v /srv/opentallas-scratch:/srv/opentallas-scratch -v $WTC:/src -e ODB=$B/6_final.odb -e OUT=$C/q_elem.lef \
  openroad/orfs:latest bash -c "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /src/tools/dsrom_q_abstract.tcl" > $C/abstract.log 2>&1
echo $? > $C/abstract.rc
M=$(awk '/^MACRO/{print $2; exit}' $C/q_elem.lef)
docker run --rm -v /srv/opentallas-scratch:/srv/opentallas-scratch -v $WTC:/src -e Q_LEF=$C/q_elem.lef -e Q_MASTER=$M -e OUT_DIR=$C/pa \
  openroad/orfs:latest bash -c "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /src/physical/abi3/dsrom_q_pin_access.tcl" > $C/pa/pa.log 2>&1
echo $? > $C/pa/pa.rc
grep -c "DRT-0073" $C/pa/pa.log > $C/pa/drt0073.count
(cd $WTC && OT_S81_Q_LEF=$C/q_elem.lef python3 tools/dsrom_s81_fulldie.py real --work $C/die > $C/die/manifest.out 2>&1)
$T/run_case.sh $C/die 16 32
grep -h "OT_LEGAL\|OT_ASSERT\|OT_PA\|OT_TIME" $C/die/run.log > $C/die/summary.txt; grep -c "DRT-0073" $C/die/run.log >> $C/die/summary.txt
echo done > $C/close.done
