#!/bin/bash
set -eu
SRC=${1:?source root}; OUT=${2:?output root}
mkdir -p "$OUT"
cd "$SRC"
python3 tools/hfd_hc_gather_cx_build.py --source-dir physical/hbm_accel_die_views/hcp/rtl --out "$OUT/gen"
cp physical/hfd_hc_gather_cx_20261009/tb_gather.sv "$OUT/gen/"
cd "$OUT/gen"
for enabled in 0 1; do
  for phase in 0 1 2; do
    name="e${enabled}_p${phase}"
    iverilog -g2012 -s tb -Ptb.ENABLE="$enabled" -Ptb.PHASE_MODE="$phase" -o "$name.sim" tb_gather.sv hfd_hc.sv ot_dsrom_su_hcpost_lane_pr_simstub.sv > "$name.build.log" 2>&1
    vvp "$name.sim" > "$name.log" 2>&1
    grep 'OT_RESULT' "$name.log"
  done
done
iverilog -g2012 -s tb -Ptb.ENABLE=1 -Ptb.PHASE_MODE=1 -o mutant.sim tb_gather.sv hfd_hc_neg.sv ot_dsrom_su_hcpost_lane_pr_simstub.sv > mutant.build.log 2>&1
set +e
vvp mutant.sim > mutant.log 2>&1
rc=$?
set -e
test "$rc" -ne 0
grep -Eq 'mismatches=[1-9]' mutant.log
printf 'MUTANT_REJECT rc=%s\n' "$rc"
printf 'PASS: six mapping arms and frozen-gather mutant\n' > ../verdict.txt
