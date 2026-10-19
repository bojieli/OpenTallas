#!/usr/bin/env bash
# MU-SLICE-GATE 10-19: benches of the SLICE-E tree at MU_NU 4 with MU-QW-AMIX (95074c8a3) carried; fleet, Verilator 5.050.
# Run from the repository root:  bash results/rtl/mu_qwen_1018/adopt_slice/runs_gate/run_one.sh CASE WORK
#   eq<M>   lockstep qfd_dv_slice2_e (SU_LT 1, HD_W130 1, MU_NU 4) == re-cut qfd_dv_slice2_e_lpf (MU_NU 4): random / +quiet / +hronly
#   lp<M>   lockstep re-cut == regenerated landed parent qfd_dv_slice2_e_lpf_lp (MU_NU 4), lp.py MUT M
#   audit   lp.py region audit (+ unland mutant must FAIL)
#   b2      dv_bench2 f j m n o on the HEAD slice (-GSU_LT=1 -GHD_W130=1 -GMU_NU=4)
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
  b2) python3 rtl/test/qwen_dv/dv_bench2.py f j m n o --vflags "-GSU_LT=1 -GHD_W130=1 -GMU_NU=4" --work "$WORK/b2" ;;
  b2n7) DV2_AM_MUT=7 python3 rtl/test/qwen_dv/dv_bench2.py n --vflags "-GSU_LT=1 -GHD_W130=1 -GMU_NU=4" --work "$WORK/b2n7" ;;
esac; echo "# exit $?"; } > "$R/$C.out" 2>&1
