#!/usr/bin/env bash
# HBM-CORES-REBAL-9: the default elaboration of the parameterised pg_lane* tops (build_split_tops --pg-params-existing,
# defaults MLAT 4 / WCOPY 0) == the committed unparameterised tops (git BASE).  Both are elaborated with yosys
# `hierarchy` and the same member RTL.  The whole design is written as RTLIL and canonicalised (rtlil_canon.py: src
# dropped, every module renamed by its body hash bottom-up), then compared.  Then the MLAT 5 / WCOPY 1 elaboration is
# checked for lat5i multipliers and the WCOPY-1 bank.
#   pg_default_eq.sh WT BASE OUT RTLDIR
set -euo pipefail
W=$1; BASE=$2; O=$3; RTL=$4; mkdir -p $O/gold
H=$(cd "$(dirname "$0")" && pwd)
Y=$HOME/.local/opentallas-tools/yosys-0.68/bin/yosys; [ -x $Y ] || Y=yosys
D=rtl/hbm_accel/cores_split/ot_hbm_su_static_pgslice_lg
BB=$W/physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2_bb.v
MEM=$(ls $RTL/*.sv | grep -v -e '_core.sv$' -e '__wrap.sv$' -e '__fshell.sv$' -e 'face_reg' | tr '\n' ' ')
for top in ot_hbm_su_pg_lanes4_core ot_hbm_su_pg_lane_exp_core ot_hbm_su_pg_lane_full_core; do
  git -C $W show $BASE:$D/$top.sv > $O/gold/$top.sv
  for side in gold gate; do
    f=$O/gold/$top.sv; [ $side = gate ] && f=$W/$D/$top.sv
    $Y -q -l $O/$top.$side.log -p "read_verilog -sv -lib $BB; read_verilog -sv -DSYNTHESIS $MEM $f; hierarchy -top $top; \
      write_rtlil $O/$top.$side.il" >/dev/null
    python3 $H/rtlil_canon.py $O/$top.$side.il $O/$top.$side.canon "\\$top"
  done
  if cmp -s $O/$top.gold.canon $O/$top.gate.canon; then
    echo "$top DEFAULT_ELAB_IDENTICAL modules $(grep -vc -e '^TOP' -e '^ ' $O/$top.gold.canon)"
  else echo "$top DIFF"; diff $O/$top.gold.canon $O/$top.gate.canon | head -20 || true; fi
  $Y -q -l $O/$top.m5w1.log -p "read_verilog -sv -lib $BB; read_verilog -sv -DSYNTHESIS $MEM $W/$D/$top.sv; \
    hierarchy -top $top -chparam MLAT 5 -chparam WCOPY 1; write_rtlil $O/$top.m5w1.il" >/dev/null
  echo "$top m5w1: qmul LAT=5 cells $(grep -c 'cell .paramod.ot_hdc_qmul_lat.LAT=s32.00000000000000000000000000000101 ' $O/$top.m5w1.il || true)," \
       "LAT=4 cells $(grep -c 'cell .paramod.ot_hdc_qmul_lat.LAT=s32.00000000000000000000000000000100 ' $O/$top.m5w1.il || true)," \
       "lat5i modules $(grep -c '^module .*ot_hdc_fp32_mul_lat5i' $O/$top.m5w1.il || true)," \
       "banks WCOPY=1 param $(awk '/^module .*pinned_bank/{m=1} m\&\&/parameter .WCOPY 1/{n++; m=0} /^end/{m=0} END{print n+0}' $O/$top.m5w1.il)"
done
