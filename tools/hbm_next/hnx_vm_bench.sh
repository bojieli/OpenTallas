#!/bin/bash
# HBM-NEXT-UNITS-VM 2026-10-19: hnx 2^19-word VM bank bench (fleet, Verilator 5.050).  Run from a bundle root (git archive of
# the lane branch) on a fleet host:  tools/hbm_next/hnx_vm_bench.sh OUT STAGE
#   STAGE all : lint (kit sources, -DSYNTHESIS, SRAM black box) + tb_hnx_vm_bank MUT 0 (SEED 1, 2) + mutants 5, 6, 7
#   STAGE m0  : MUT 0 only (PASS: 'TB_HNX_VM PASS')      STAGE m5|m6|m7 : one mutant (must print 'TB_HNX_VM FAIL')
# tb_hnx_vm_bank: phase A lockstep vs the d4g SE/NE master hfd_vms_bank_native_q0_faces on the lower 2^18 words + mirror
# (every output, every edge); phase B full 2^19 fill / read-back scoreboard (A0 + A1 + mirror, all 7 write / 6 read
# owners, constant latency, status 0); phase C mirror row[10] sector -> FAULT.
set -u
B=$(pwd); O=$(realpath -m "${1:?OUT}"); ST=${2:-all}; mkdir -p "$O"
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
VL=$(command -v verilator); echo "verilator: $VL $($VL --version)" > "$O/verilator.txt"
V(){ echo "$(date -Is) $*" | tee -a "$O/verdict_$ST.txt"; }
V "start host=$(hostname) bundle=$(cat $B/BUNDLE_COMMIT 2>/dev/null) $($VL --version)"
H=rtl/hbm_next/vm; D=rtl/hbm_accel/generic/vm/static
HNX=($H/hnx_vms_bank_q0_faces.sv $H/ot_hnx_vms_bank_q0_core.sv $H/ot_hnx_vms_bank_q0_body.sv $H/ot_hnx_vms_ce_counter_pipe.sv)
D4G=($D/faces_q0/hfd_vms_bank_native_q0_faces.sv $D/faces_q0/ot_vms_bank_q0_faces_core.sv $D/faces_q0/ot_vms_bank_q0_faces_body.sv $D/ot_vms_ce_counter_pipe.sv)
MEM=physical/asap7_memory_macros_v2/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
MEMBB=physical/asap7_memory_macros_v2/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2_bb.v
build_run(){ # tag "-G..."
  local d=$O/obj_$1; rm -rf $d
  verilator --binary --timing -j 8 -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN --top-module tb_hnx_vm_bank $2 -Mdir $d -o V$1 \
    $H/tb/tb_hnx_vm_bank.sv "${HNX[@]}" "${D4G[@]}" $MEM > $O/build_$1.log 2>&1 || { sleep 5; verilator --binary --timing -j 1 \
    -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN --top-module tb_hnx_vm_bank $2 -Mdir $d -o V$1 \
    $H/tb/tb_hnx_vm_bank.sv "${HNX[@]}" "${D4G[@]}" $MEM > $O/build_$1.log 2>&1; }
  ( cd $O && $d/V$1 > $O/$1.log 2>&1; echo RUN_RC=$? >> $O/$1.log )
  V "$1: $(grep -h '^HNX_VM_\|^TB_HNX_VM' $O/$1.log | tr '\n' ' ' | cut -c1-900)"; rm -rf $d
}
lint(){
  printf '%s\n' 'module ot_lint_top; hnx_vms_bank_q0_faces u_top (); endmodule' > $O/ot_lint_top.sv
  verilator --lint-only -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-MODMISSING -DSYNTHESIS \
    --top-module ot_lint_top $O/ot_lint_top.sv "${HNX[@]}" $MEMBB > $O/lint.log 2>&1
  V "lint rc=$? errors=$(grep -c '%Error' $O/lint.log)"
}
case $ST in
  all) lint
       build_run m0s1 "-GMUT=0 -GSEED=1" & build_run m0s2 "-GMUT=0 -GSEED=2 -GNA=6000" &
       build_run m5 "-GMUT=5" & build_run m6 "-GMUT=6" & build_run m7 "-GMUT=7" & wait
       np=$(grep -h '^TB_HNX_VM PASS MUT=0' $O/m0s1.log $O/m0s2.log | wc -l)
       nf=$(grep -l '^TB_HNX_VM FAIL MUT=[567]' $O/m5.log $O/m6.log $O/m7.log | wc -l)
       [ "$np" = 2 ] && V "HNX_VM_BENCH PASS 2/2" || V "HNX_VM_BENCH FAIL $np/2"
       [ "$nf" = 3 ] && V "HNX_VM_MUTANTS FAIL-AS-REQUIRED 3/3" || V "HNX_VM_MUTANTS ESCAPED $((3-nf))/3";;
  m0) build_run m0s1 "-GMUT=0 -GSEED=1"; grep -q '^TB_HNX_VM PASS MUT=0' $O/m0s1.log && V "HNX_VM_BENCH PASS" || V "HNX_VM_BENCH FAIL";;
  m5|m6|m7) build_run $ST "-GMUT=${ST#m}"; grep -q '^TB_HNX_VM FAIL' $O/$ST.log && V "HNX_VM_BENCH FAIL ($ST)" || V "HNX_VM_BENCH PASS ($ST)";;
esac
V "done"
