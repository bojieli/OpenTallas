#!/bin/bash
# run_vsw_lr_eq.sh RTLDIR SIMSRAM [SEED]: iverilog lockstep ot_s81sl_vsw LR=1 vs LR=0 (kit rtl dir = vsw VERILOG_FILES minus the
# SRAM black box; SIMSRAM = the 128x256 1r1w provider simulation model).  Then the NEGATIVE CONTROL MUTANT: the same bench on
# a copy of ot_s81sl_vsw.sv whose LR=1 lane register loads u instead of g (lg <= ln_u0) must report VSW_LR_EQ FAIL.
# Exit 0 only when the real run PASSes and the mutant FAILs.
set -euo pipefail
R=$1; S=$2; SEED=${3:-12345}; D=$(cd "$(dirname "$0")" && pwd); O=$(mktemp -d)
F=$(ls $R/*.sv | grep -v _bb)
iverilog -g2012 -DSYNTHESIS_OFF -o $O/sim -s tb_s81sl_vsw_lr_eq $D/tb_s81sl_vsw_lr_eq.sv $S $F 2>&1 | grep -v "warning\|Port .* of\|padding\|truncat\|Pruning\|^ *: " | head -20 || true
vvp -n $O/sim +seed=$SEED | tail -8 | tee $O/real.txt
mkdir $O/mut; for f in $F; do cp $f $O/mut/; done
grep -q 'lg <= ln_g0;' $O/mut/ot_s81sl_vsw.sv
sed -i 's/lg <= ln_g0;/lg <= ln_u0;/' $O/mut/ot_s81sl_vsw.sv
iverilog -g2012 -DSYNTHESIS_OFF -o $O/simm -s tb_s81sl_vsw_lr_eq $D/tb_s81sl_vsw_lr_eq.sv $S $O/mut/*.sv >/dev/null 2>&1
echo "--- negative control mutant (lg <= ln_u0):"
vvp -n $O/simm +seed=$SEED | tail -3 | tee $O/mut.txt
rc=1; grep -q 'VSW_LR_EQ PASS' $O/real.txt && grep -q 'VSW_LR_EQ FAIL' $O/mut.txt && rc=0
echo "VSW_LR_EQ_GATE rc=$rc (real PASS + mutant FAIL)"
rm -rf $O; exit $rc
