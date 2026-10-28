#!/bin/bash
# MESO-STRAP-1 k-induction driver for the strap-form sby files (fv_ca2_strap*.sby, fv_ca2_strapmut.sby, fv_ca2_straptmo.sby):
#   fv_strap_kind.sh SBY TASK B K   (inside the ORFS docker image: sby + yosys-abc; safe to run many in parallel)
# Same flow as fv_ca2_kind.sh (base bmc3 -F B, step scorr; dc2; ind -F K -u) with per-(sby, task) log/result names.
s=$1; t=$2; bf=$3; kf=$4; b=$(basename $s .sby)
rm -rf ${b}_$t
sby -f $s $t > sby_${b}_$t.log 2>&1
( cd ${b}_$t && timeout ${FV_TIMEOUT:-7200} yosys-abc -c "read_aiger model/design_aiger.aig; fold; strash; bmc3 -F $bf; scorr; dc2; ind -F $kf -u" ) > kind_${b}_$t.log 2>&1
echo "$t B=$bf K=$kf base=$(grep -c "No output asserted in $bf frames" kind_${b}_$t.log) ind=$(grep -c "Networks are equivalent" kind_${b}_$t.log) fail=$(grep -c "Output .* was asserted in frame" kind_${b}_$t.log)" >> kind_results_${b}.txt
