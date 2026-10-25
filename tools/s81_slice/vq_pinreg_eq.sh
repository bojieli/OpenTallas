#!/bin/bash
# vq_pinreg_eq.sh <outdir> [base|mut] (cwd = repo root): S81-NATIVE3 equivalence bench of ot_s81sl_vq (pin-registered
# m_v/um_v/y_v) against the CLOSED view's RTL at b6d9d4515.  base must PASS; mut (+define+OT_VQ_MUT_PINREG) and mutwreg (+define+OT_VQ_MUT_WREG) must FAIL.
set -u; O=$1; M=${2:-base}; mkdir -p $O
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
REF=${VQ_REF:-b6d9d4515}
{ [ -n "${VQ_REF_FILE:-}" ] && cat "$VQ_REF_FILE" || git show $REF:rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vq.sv; } | sed 's/^module ot_s81sl_vq /module ot_s81sl_vq_ref /' > $O/ot_s81sl_vq_ref.sv
grep -q "module ot_s81sl_vq_ref" $O/ot_s81sl_vq_ref.sv || { echo "BENCH_SETUP_FAILED ref"; exit 4; }
. physical/ref_tile/s81sl_vq/kit.env
DEF="${VQ_DEF:-}"; [ "$M" = mut ] && DEF="+define+OT_VQ_MUT_PINREG"; [ "$M" = mutwreg ] && DEF="+define+OT_VQ_MUT_WREG" ; [ "$M" = mutbfq ] && DEF="+define+OT_VQ_MUT_BFQ"; [ "$M" = mutblkf ] && DEF="+define+OT_VQ_MUT_BLKF"   # S81-VQFIX: macro write-port register misaligned
$V --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD $DEF --top-module tb_vq_pinreg_eq -Mdir $O/obj_$M $SRCS $O/ot_s81sl_vq_ref.sv \
  physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v rtl/dsrom_sys/s81_dv/slice/test/tb_vq_pinreg_eq.sv \
  --build-jobs ${J:-4} > $O/build_$M.log 2>&1 || { echo "BUILD_FAILED"; tail -n 8 $O/build_$M.log; exit 3; }
$O/obj_$M/Vtb_vq_pinreg_eq > $O/run_$M.log 2>&1; grep -E "MISMATCH|^VQ|^PASS|^FAIL" $O/run_$M.log | head -14
if [ "$M" = base ]; then grep -q '^PASS' $O/run_$M.log && exit 0; exit 1; fi
grep -q '^FAIL' $O/run_$M.log && { echo "NEGATIVE_CONTROL_FAILED_AS_EXPECTED $M"; exit 0; }; echo "NEGATIVE_CONTROL_PASSED $M (bench blind)"; exit 1
