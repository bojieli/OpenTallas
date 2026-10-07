#!/bin/bash
# run_bench.sh <outdir> <PQ 0|1> [MUT 0|1|2] [NEG 0..3]   (cwd = repo root)  exact bench of the banked HA2 reducer
set -u; O=$1; PQ=$2; MUT=${3:-0}; NEG=${4:-0}; mkdir -p $O
F=$(sed 's#^#  #' rtl/hbm_accel/ha2_ar/tb_ha2_tu_owner_banked.f | tr '\n' ' ')
[ -x $O/obj/Vtb_ha2_tu_owner_banked ] || verilator --binary --timing -O1 -Wno-fatal -Wno-WIDTH --top-module tb_ha2_tu_owner_banked -GPQ=$PQ -GHALF=${HALF:-0} -GMUT=$MUT -Mdir $O/obj $F rtl/hbm_accel/ha2_ar/tb_ha2_tu_owner_banked.sv --build-jobs 4 > $O/build.log 2>&1 || { echo BUILD_FAILED; tail -n 5 $O/build.log; exit 3; }
(cd $O && ./obj/Vtb_ha2_tu_owner_banked ${NEG:+$([ "$NEG" != 0 ] && echo +NEG=$NEG)} > run.log 2>&1); rc=$?
grep -E "^S[0-9]|^PASS|NEGATIVE|Fatal" $O/run.log | cut -c1-200
exit $rc
