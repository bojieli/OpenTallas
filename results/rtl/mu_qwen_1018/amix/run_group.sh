#!/usr/bin/env bash
# MU-QW-AMIX 10-19: the root argmax merge's one-user rule checked in RTL (qfd_dv_scalar2 MU_NU > 1 mixed-merge fault,
# user carried in the AMI / AMV / TOK tag, slice2 st[27:26] = token user).  Fleet, Verilator 5.050 (the closure
# daemon's), ONE Verilator build per ot-run job.  Run from the repository root:
#   bash results/rtl/mu_qwen_1018/amix/run_group.sh GROUP WORK
# Groups:  F0 / F1 / F2   MU_NU 1 identity: every dv_bench2 bench a-g, i, j on master (0) / W face (1) / E face (2)
#          G0 / G1 / G2   MU_NU 4 on the same face: a-g, i, j; bench m (4 users, seeds 21 / 22, token users checked);
#                         bench n (mixed merge must fault + legal tokens / users)
#          N0 / N1 / N2   NEG: bench n with DV2_AM_MUT 7 (qfd_dv_scalar2 MU_MUT 2: the check dropped) -> must FAIL
#          H1 / H4        bench h (12-slice master chain SETID) at MU_NU 1 / 4
#          FACES1/FACES4  tb_qfd_dv2_faces (W1 W0 E0 E1 chain) MUT 0 at MU_NU 1 / 4
# Logs: results/rtl/mu_qwen_1018/amix/runs/<case>.out
set -u
G=$1; WORK=$2
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
R=results/rtl/mu_qwen_1018/amix/runs; mkdir -p "$R" "$WORK"
verilator --version > "$R/verilator_version_$G.txt"
B=rtl/test/qwen_dv/dv_bench2.py
run() { # case env... -- args
  local c=$1; shift; local envs=(); while [ "$1" != "--" ]; do envs+=("$1"); shift; done; shift
  { echo "# case $c env ${envs[*]} args $* host $(hostname) $(date -Is) commit $(cat SOURCE_COMMIT 2>/dev/null)";
    env "${envs[@]}" python3 "$B" "$@"; echo "# exit $?"; } > "$R/$c.out" 2>&1
}
case $G in
F0|F1|F2) f=${G#F}
  run F${f}_nu1_ag DV2_FACE=$f DV2_MU_NU=1 -- a b c d e f g i j --work "$WORK/F${f}_nu1" ;;
G0|G1|G2) f=${G#G}
  run F${f}_nu4_ag DV2_FACE=$f DV2_MU_NU=4 -- a b c d e f g i j --work "$WORK/F${f}_nu4"
  for s in 21 22; do run F${f}_nu4_m_s$s DV2_FACE=$f DV2_MU_NU=4 DV2_SEED=$s -- m --work "$WORK/F${f}_nu4"; done
  run F${f}_nu4_n DV2_FACE=$f DV2_MU_NU=4 -- n --work "$WORK/F${f}_nu4" ;;
N0|N1|N2) f=${G#N}
  run NEG_n_am7_f$f DV2_FACE=$f DV2_MU_NU=4 DV2_AM_MUT=7 -- n --work "$WORK/N$f" ;;
H1|H4) nu=${G#H}
  run F0_nu${nu}_h DV2_FACE=0 DV2_MU_NU=$nu -- h --work "$WORK/H$nu" ;;
FACES1|FACES4) nu=${G#FACES}; c=FACES_mut0_nu$nu
  S=$(python3 -c "import sys; sys.path.insert(0,'rtl/test/qwen_dv'); import dv_bench2 as D; print(' '.join(s for s in D.SRCS2 if not s.endswith('tb_qfd_dv2.sv')))")
  { echo "# case $c host $(hostname) $(date -Is) commit $(cat SOURCE_COMMIT 2>/dev/null)";
    verilator --binary --timing -O2 -j 8 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --x-assign 0 --x-initial 0 \
      --top-module tb_qfd_dv2_faces -GMUT=0 -GMU_NU=$nu -Mdir "$WORK/$c" -o sim $S rtl/test/qwen_dv/tb_qfd_dv2_faces.sv \
      > "$WORK/$c.build.log" 2>&1 || { echo BUILD FAIL; tail -30 "$WORK/$c.build.log"; };
    "$WORK/$c/sim"; echo "# exit $?"; } > "$R/$c.out" 2>&1 ;;
LINT)
  S=$(python3 -c "import sys; sys.path.insert(0,'rtl/test/qwen_dv'); import dv_bench2 as D; print(' '.join(D.SRCS2))")
  for nu in 1 4; do verilator --lint-only -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --top-module tb_qfd_dv2 -GMU_NU=$nu -GFACE=1 $S > "$R/lint_nu$nu.out" 2>&1; echo "# exit $?" >> "$R/lint_nu$nu.out"; done ;;
esac
