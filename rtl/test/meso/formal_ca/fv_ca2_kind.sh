#!/bin/bash
# MESO-COUNT-2 k-induction driver: fv_ca2_kind.sh SBY TASK B K  (run inside the ORFS docker image: sby + yosys-abc)
# builds the task's model (sby bmc depth 1), then  base: bmc3 -F B ; step: scorr; dc2; ind -F K -u  (needs K <= B)
# appends "TASK base=1 ind=1" (PROVEN) to kind_results_<sby>.txt.  Final sweeps: B 260 / K 250 (D4 and D8 in-range); lap/tag range samples: D4 B 620/K 600, D8 B 1100/K 1080.
s=$1; t=$2; bf=$3; kf=$4; b=$(basename $s .sby)
rm -rf ${b}_$t
sby -f $s $t >/dev/null 2>&1
( cd ${b}_$t && yosys-abc -c "read_aiger model/design_aiger.aig; fold; strash; bmc3 -F $bf; scorr; dc2; ind -F $kf -u" ) > kind_$t.log 2>&1
echo "$t base=$(grep -c "No output asserted in $bf frames" kind_$t.log) ind=$(grep -c "Networks are equivalent" kind_$t.log)" >> kind_results_$b.txt
