#!/usr/bin/env bash
# FABLE-FIX-S81-SEQHOST (2026-11-19): equivalence gate of the restructured dsdv_mu_hwin (0 cycles) against the 11-18
# source (test/ref/dsdv_mu_hwin_ref_1119.sv).  Verilator 5.050 + yosys 0.68 (~/.local/opentallas-tools).
#   1 lockstep: full size (NSLOT 47, NEV 8) and small tables, random episodes, outputs equal on every edge;
#     dut mutants MUT 3 / 4 / 5 must be caught;
#   2 age cell: one-step induction of dsdv_mu_hwin_age against its definition (32-bit ages, incl. the 2^31 wrap of
#     the late flag that no simulation reaches) + a broken cell must fail;
#   3 bounded SAT miter (yosys sat -seq) of both modules at NSLOT 3 / NEV 2, every input free.
# Usage: run_mu_hwin_eq.sh OUTDIR [EPISODES]   (light: 1 thread per step; run it through ot-run for big EPISODES)
set -u
R=$(cd "$(dirname "$0")/../../../../.." && pwd)
O=$(realpath -m "${1:-$(mktemp -d)}"); mkdir -p "$O"; EPS=${2:-300}
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$HOME/.local/opentallas-tools/bin:$PATH
U=$R/rtl/dsrom_sys/s81_dv/unit
F="$R/rtl/lib/ot_rst_relay.sv $U/dsdv_mu_hwin.sv $U/test/ref/dsdv_mu_hwin_ref_1119.sv $U/test/tb_mu_hwin_eq.sv"
bad=0
build() { n=$1; shift
  verilator --binary --timing -j "${OT_THREADS:-4}" -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style --top-module tb_mu_hwin_eq "$@" $F \
    --Mdir "$O/obj_$n" -o tb > "$O/build_$n.log" 2>&1 || { echo "BUILD_FAIL $n"; bad=1; return 1; }; }
run() { n=$1; e=$2; s=$3; "$O/obj_$n/tb" +EPS=$e +SEED=$s > "$O/run_${n}_$s.log" 2>&1; grep -E '^HWIN_EQ' "$O/run_${n}_$s.log" | sed "s/^/[$n seed $s] /"; }
if [ "${STEPS:-123}" != "${STEPS#*1}" ] || [ -z "${STEPS:-}" ]; then
build full && for s in 1 2 3; do run full "$EPS" $s; grep -q '^HWIN_EQ PASS' "$O/run_full_$s.log" || bad=1; done
build s5 +define+NSLOT=5 +define+NEV=3 && { run s5 $((EPS * 10)) 11; grep -q '^HWIN_EQ PASS' "$O/run_s5_11.log" || bad=1; }
build s3 +define+NSLOT=3 +define+NEV=2 && { run s3 $((EPS * 10)) 12; grep -q '^HWIN_EQ PASS' "$O/run_s3_12.log" || bad=1; }
build s8 +define+NSLOT=8 +define+NEV=8 && { run s8 $((EPS * 10)) 13; grep -q '^HWIN_EQ PASS' "$O/run_s8_13.log" || bad=1; }
for m in 3 4 5; do build mut$m +define+NSLOT=8 +define+NEV=8 +define+DMUT=$m && { run mut$m $EPS 21
  if grep -q '^HWIN_EQ PASS' "$O/run_mut${m}_21.log"; then echo "mutant $m NOT detected"; bad=1; else echo "mutant $m detected (FAIL as required)"; fi; }
done
fi
if [ "${STEPS:-123}" != "${STEPS#*2}" ] || [ -z "${STEPS:-}" ]; then
( cd "$O" && yosys -q -l age_ind.log -p "read_verilog -sv $U/dsdv_mu_hwin.sv $U/test/hwin_age_ind.sv; hierarchy -top hwin_age_ind; proc; setattr -mod -unset keep_hierarchy; flatten; connect -set p_b dut.b; connect -set p_lm dut.lm; connect -set p_hz dut.hz; connect -set p_hc dut.hc; opt -fast; memory; opt -fast; sat -tempinduct -set-init-zero -maxsteps 3 -prove ok 1 -verify -show-inputs -timeout 3600" ) > "$O/age_ind.out" 2>&1 \
  && grep -q 'Induction step proven: SUCCESS' "$O/age_ind.log" && echo "AGE_IND PASS (dsdv_mu_hwin_age == definition, induction)" || { echo "AGE_IND FAIL"; bad=1; }
sed 's/b\[31:21\] == 11.h400/b[31:21] == 11'"'"'h401/' "$U/dsdv_mu_hwin.sv" > "$O/hwin_agemut.sv"
( cd "$O" && yosys -q -l age_ind_mut.log -p "read_verilog -sv $O/hwin_agemut.sv $U/test/hwin_age_ind.sv; hierarchy -top hwin_age_ind; proc; setattr -mod -unset keep_hierarchy; flatten; connect -set p_b dut.b; connect -set p_lm dut.lm; connect -set p_hz dut.hz; connect -set p_hc dut.hc; opt -fast; memory; opt -fast; sat -tempinduct -set-init-zero -maxsteps 3 -prove ok 1 -verify -timeout 3600" ) > "$O/age_ind_mut.out" 2>&1 \
  && { echo "AGE_IND mutant NOT detected"; bad=1; } || echo "AGE_IND mutant detected (FAIL as required)"
fi
if [ "${STEPS:-123}" != "${STEPS#*3}" ] || [ -z "${STEPS:-}" ]; then
( cd "$O" && yosys -q -l bmc.log -p "read_verilog -sv -DSYNTHESIS $R/rtl/lib/ot_rst_relay.sv $U/dsdv_mu_hwin.sv $U/test/ref/dsdv_mu_hwin_ref_1119.sv $U/test/hwin_eq_miter.sv; hierarchy -top hwin_eq_miter; proc; setattr -mod -unset keep_hierarchy; flatten; async2sync; opt -fast; memory -nomap; memory_map; opt; sat -seq ${BMC_STEPS:-22} -set-init-zero -prove-asserts -prove ok 1 -verify -timeout ${BMC_TIMEOUT:-20000}" ) > "$O/bmc.out" 2>&1 \
  && grep -q 'SUCCESS' "$O/bmc.log" && echo "BMC PASS (NSLOT 3 NEV 2, ${BMC_STEPS:-22} edges, all inputs free)" || { echo "BMC FAIL"; bad=1; }
fi
[ $bad = 0 ] && echo "MU_HWIN_EQ_GATE PASS" || echo "MU_HWIN_EQ_GATE FAIL"; exit $bad
