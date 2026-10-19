#!/usr/bin/env bash
# MU-SLICE-GATE 10-19: benches of the SLICE-E tree at MU_NU 4 with MU-QW-AMIX (95074c8a3) carried; fleet, Verilator 5.050.
# Run from the repository root:  bash rtl/test/qwen_dv/run_mu_slice_gate.sh CASE WORK
#   eq<M>   lockstep qfd_dv_slice2_e (SU_LT 1, HD_W130 1, MU_NU 4) == re-cut qfd_dv_slice2_e_lpf (MU_NU 4): random / +quiet / +hronly
#   lp<M>   lockstep re-cut == regenerated landed parent qfd_dv_slice2_e_lpf_lp (MU_NU 4), lp.py MUT M
#   audit   lp.py region audit (+ unland mutant must FAIL)
#   b2      dv_bench2 f j k q m n o on the HEAD slice (-GSU_LT=1 -GHD_W130=1 -GMU_NU=4)
#   faces<M> tb_qfd_dv2_faces (W1 W0 E0 E1 chain of qfd_dv_slice2_w / _e at SU_LT 1, HD_W130 1, MU_NU 4), MUT M (0 PASS; 11/12 FAIL)
#   b2k14   NEG: dv_bench2 k with MUT 14 (redstn2 last-k selection off) -> must FAIL
#   b2q15   NEG: dv_bench2 q (MU users 1-3 + kc together) with MUT 15 (kcm1 read at the pre-fix [58:51]) -> must FAIL
#   b2n7    NEG: dv_bench2 n with DV2_AM_MUT 7 (root mixed-merge check dropped) -> must FAIL
set -u
C=$1; WORK=$2; R=results/rtl/mu_qwen_1018/adopt_slice/runs_gate; mkdir -p "$R" "$WORK"
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
export VERILATOR=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
{ echo "# case $C host $(hostname) $(date -Is) commit $(cat SOURCE_COMMIT 2>/dev/null) $(verilator --version)"
case $C in
  eq*) bash rtl/test/qwen_dv/run_slice2_e_lpf.sh "$WORK/$C" eq ${C#eq}; cp "$WORK/$C"/eq*.log "$R/" 2>/dev/null ;;
  lp*) bash rtl/test/qwen_dv/run_slice2_e_lpf.sh "$WORK/$C" lp ${C#lp} ;;
  audit) bash rtl/test/qwen_dv/run_slice2_e_lpf.sh "$WORK/$C" audit ;;
  b2) python3 rtl/test/qwen_dv/dv_bench2.py f j k q m n o --vflags "-GSU_LT=1 -GHD_W130=1 -GMU_NU=4" --work "$WORK/b2" ;;
  faces*) m=${C#faces}
    S=$(python3 -c "import sys; sys.path.insert(0,'rtl/test/qwen_dv'); import dv_bench2 as D; print(' '.join(s for s in D.SRCS2 + D.XSRCS if not s.endswith(('tb_qfd_dv2.sv', 'qfd_dv_slice2_faces.sv'))))")
    verilator --binary --timing -O2 -j 16 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --x-assign 0 --x-initial 0 \
      --top-module tb_qfd_dv2_faces -GMUT=$m -GMU_NU=4 -GSU_LT=1 -GHD_W130=1 -Mdir "$WORK/$C" -o sim $S rtl/qwen_dv/qfd_dv_slice2_faces.sv \
      rtl/test/qwen_dv/tb_qfd_dv2_faces.sv > "$WORK/$C.build.log" 2>&1 || { echo BUILD FAIL; tail -30 "$WORK/$C.build.log"; }
    "$WORK/$C/sim" ;;
  b2k14) python3 rtl/test/qwen_dv/dv_bench2.py k --mut 14 --vflags "-GSU_LT=1 -GHD_W130=1 -GMU_NU=4" --work "$WORK/b2k14" ;;
  b2q15) python3 rtl/test/qwen_dv/dv_bench2.py q --mut 15 --vflags "-GSU_LT=1 -GHD_W130=1 -GMU_NU=4" --work "$WORK/b2q15" ;;
  b2n7) DV2_AM_MUT=7 python3 rtl/test/qwen_dv/dv_bench2.py n --vflags "-GSU_LT=1 -GHD_W130=1 -GMU_NU=4" --work "$WORK/b2n7" ;;
esac; echo "# exit $?"; } > "$R/$C.out" 2>&1
cat "$R/$C.out"
