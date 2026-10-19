#!/usr/bin/env bash
# MU-ADOPT-SLICE 10-19: R4 (per-user chunked LM-head argmax, qfd_dv_amax_mu) adopted into qfd_dv_slice2 (MU_NU) and its
# generated faces qfd_dv_slice2_w / _e.  Fleet, Verilator 5.050 (the closure daemon's).  Run from the repository root:
#   bash results/rtl/mu_qwen_1018/adopt_slice/run_group.sh GROUP WORK
# Groups (one ot-run job each): F0 / F1 / F2 = every dv_bench2 bench (a-g, i, j; h on the 12-slice master chain) at
# MU_NU 1 and 4 on the master (F0), the W face (F1), the E face (F2), then bench m (4 users) at MU_NU 4 (2 seeds);
# NEG = bench m negatives (MU_NU 1; qfd_dv_amax_mu mutants 1-4 on the W face, 2 on the E face; AM_MUT 6 = root merge not
# restarted per token; gap 12 = STN while results pending -> stn_pend fault; slice mutants 11 / 12 at MU_NU 4); FACES = tb_qfd_dv2_faces (W1 W0 E0 E1 chain) at MU_NU 1 / 4 + its mutants 11 / 12 at MU_NU 4.
# Logs: results/rtl/mu_qwen_1018/adopt_slice/runs/<case>.out; sim logs of the identity compare in WORK.
set -u
G=$1; WORK=$2
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
R=results/rtl/mu_qwen_1018/adopt_slice/runs; mkdir -p "$R" "$WORK"
verilator --version > "$R/verilator_version_$G.txt"
B=rtl/test/qwen_dv/dv_bench2.py
run() { # case env... -- args
  local c=$1; shift; local envs=(); while [ "$1" != "--" ]; do envs+=("$1"); shift; done; shift
  { echo "# case $c env ${envs[*]} args $* host $(hostname) $(date -Is) commit $(cat SOURCE_COMMIT 2>/dev/null)";
    env "${envs[@]}" python3 "$B" "$@"; echo "# exit $?"; } > "$R/$c.out" 2>&1
}
case $G in
ONE)  # one build per ot-run job (a slice2 Verilator build peaks at ~12-16 GB; 4 in one 48 GB unit were OOM-killed)
  c=$3; shift 3; envs=(); while [ "$1" != "--" ]; do envs+=("$1"); shift; done; shift
  run "$c" "${envs[@]}" -- "$@" ;;
FONE)  # one tb_qfd_dv2_faces build: FONE WORK MUT NU
  m=$3; nu=$4; c=FACES_mut${m}_nu${nu}
  S=$(python3 -c "import sys; sys.path.insert(0,'rtl/test/qwen_dv'); import dv_bench2 as D; print(' '.join(s for s in D.SRCS2 if not s.endswith('tb_qfd_dv2.sv')))")
  { echo "# case $c host $(hostname) $(date -Is) commit $(cat SOURCE_COMMIT 2>/dev/null)";
    verilator --binary --timing -O2 -j 8 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --x-assign 0 --x-initial 0 \
      --top-module tb_qfd_dv2_faces -GMUT=$m -GMU_NU=$nu -Mdir "$WORK/$c" -o sim $S rtl/test/qwen_dv/tb_qfd_dv2_faces.sv \
      > "$WORK/$c.build.log" 2>&1 || { echo BUILD FAIL; tail -30 "$WORK/$c.build.log"; };
    "$WORK/$c/sim"; echo "# exit $?"; } > "$R/$c.out" 2>&1 ;;
F0|F1|F2)
  f=${G#F}
  for nu in 1 4; do
    run ${G}_nu${nu}_ag DV2_FACE=$f DV2_MU_NU=$nu -- a b c d e f g i j --work "$WORK/${G}_nu$nu" &
    [ "$f" = 0 ] && run ${G}_nu${nu}_h DV2_FACE=0 DV2_MU_NU=$nu -- h --work "$WORK/${G}_nu${nu}_h" &
  done
  wait
  for s in 21 22; do run ${G}_nu4_m_s$s DV2_FACE=$f DV2_MU_NU=4 -- m --work "$WORK/${G}_nu4" < /dev/null; done
  if [ "$f" = 0 ]; then
    # gaps 12 / 14: the next STN issues while results are pending -> stn_pend fault (NEG_m_gap12_stnpend)
    for g in 16 20 24 30; do DV2_GAP=$g run F0_nu4_m_gap$g DV2_FACE=0 DV2_MU_NU=4 DV2_GAP=$g -- m --work "$WORK/F0_nu4"; done
  fi ;;
NEG)
  run NEG_m_nu1_w DV2_FACE=1 DV2_MU_NU=1 -- m --work "$WORK/NEG_nu1" &
  for m in 1 2 3 4; do run NEG_m_am$m DV2_FACE=1 DV2_MU_NU=4 DV2_AM_MUT=$m -- m --work "$WORK/NEG_am$m" & done
  run NEG_m_am2_e DV2_FACE=2 DV2_MU_NU=4 DV2_AM_MUT=2 -- m --work "$WORK/NEG_am2e" &
  run NEG_i_mut11_nu4 DV2_FACE=1 DV2_MU_NU=4 -- i --mut 11 --work "$WORK/NEG_s11" &
  run NEG_j_mut12_nu4 DV2_FACE=1 DV2_MU_NU=4 -- j --mut 12 --work "$WORK/NEG_s12" &
  run NEG_m_am6_rootnoclr DV2_FACE=1 DV2_MU_NU=4 DV2_AM_MUT=6 -- m --work "$WORK/NEG_am6" &
  run NEG_m_gap12_stnpend DV2_FACE=0 DV2_MU_NU=4 DV2_GAP=12 -- m --work "$WORK/NEG_g12" &
  wait ;;
FACES)
  S=$(python3 -c "import sys; sys.path.insert(0,'rtl/test/qwen_dv'); import dv_bench2 as D; print(' '.join(s for s in D.SRCS2 if not s.endswith('tb_qfd_dv2.sv')))")
  for spec in "0 1" "0 4" "11 4" "12 4"; do
    set -- $spec; m=$1; nu=$2; c=FACES_mut${m}_nu${nu}
    ( { echo "# case $c host $(hostname) $(date -Is) commit $(cat SOURCE_COMMIT 2>/dev/null)";
        verilator --binary --timing -O2 -j 8 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --x-assign 0 --x-initial 0 \
          --top-module tb_qfd_dv2_faces -GMUT=$m -GMU_NU=$nu -Mdir "$WORK/$c" -o sim $S rtl/test/qwen_dv/tb_qfd_dv2_faces.sv \
          > "$WORK/$c.build.log" 2>&1 || { echo BUILD FAIL; tail -30 "$WORK/$c.build.log"; };
        "$WORK/$c/sim"; echo "# exit $?"; } > "$R/$c.out" 2>&1 ) &
  done
  wait ;;
DHUSER)
  H=results/rtl/mu_qwen_1018/adopt_slice
  dcase() { # case mut seed plusargs
    local c=$1 m=$2 s=$3 pa=$4
    ( { echo "# case $c MUT=$m SEED=$s plusargs '$pa' host $(hostname) $(date -Is) commit $(cat SOURCE_COMMIT 2>/dev/null)";
        sha256sum rtl/qwen_split/mu/qfd_sys_face_mu_dhuser.sv $H/tb_dhuser.sv;
        verilator --binary --timing -Wno-fatal -Wno-lint -Wno-style --top-module tb_dhuser -GMUT=$m -GSEED=$s \
          -Mdir "$WORK/$c" -o sim rtl/qwen_split/mu/qfd_sys_face_mu_dhuser.sv $H/tb_dhuser.sv > "$WORK/$c.build.log" 2>&1 \
          || { echo BUILD FAIL; tail -30 "$WORK/$c.build.log"; };
        "$WORK/$c/sim" $pa; echo "# exit $?"; } > "$R/$c.out" 2>&1 ) &
  }
  grep -q "always @\* seq_dh = {dh_prog, dh_run};" rtl/qwen_split/qfd_sys_face.sv && \
  grep -q "dh_run\[42\] <= ev_stage; dh_run\[41:36\] <= ev_stage ? ta\[5:0\]" rtl/qwen_split/qfd_sys_face.sv \
    && echo "seq_dh field map OK (h_start [42], stage [41:36])" > "$R/dhuser_fieldmap.out" \
    || echo "seq_dh field map MOVED: FAIL" > "$R/dhuser_fieldmap.out"
  dcase dhuser_pass_s7 0 7 ""; dcase dhuser_pass_s11 0 11 ""; dcase dhuser_slip_pass 0 7 "+slip"
  dcase dhuser_mut1 1 7 ""; dcase dhuser_mut3 3 7 ""; dcase dhuser_mut2_slip 2 7 "+slip"
  wait ;;
esac
