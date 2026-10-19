#!/usr/bin/env bash
# MU-DQ-SLICEKC 10-19: dv_bench2 witnesses of the kitted Qwen slice faces (qfd_dv_slice2_w / _e at SU_LT 1, HD_W130 1)
# with the redstn2 last-k selection (STN cmd[66:59] = kc - 1) at MU_NU 1 and 4.  Fleet, Verilator 5.050 (the closure
# daemon's).  One Verilator build per ot-run job.  Run from the source root:
#   bash results/rtl/mu_qwen_1018/slicekc/run_kc.sh CASE WORK
# Cases:
#   P<f>_<nu>   f = W|E, nu = 1|4: benches a b c d e f g i j k (+ m o n at nu 4) -> PASS; at nu 1 also m / o -> FAIL
#               (one user: heads collide / overlap not faulted) as NEG_<b>_nu1_<f>
#   H<f>_<nu>   bench h (12-slice chain) -> PASS
#   K14_<f>     NEG: bench k, MUT 14 (kcm1 ignored), nu 4 -> FAIL
#   AM<m>_<f>   NEG: DV2_AM_MUT m (1..4, 6 bench m; 5 bench o; 7 bench n), nu 4 -> FAIL
# Logs: results/rtl/mu_qwen_1018/slicekc/runs/<case>.out
set -u
C=$1; WORK=$2
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
R=results/rtl/mu_qwen_1018/slicekc/runs; mkdir -p "$R" "$WORK"
B=rtl/test/qwen_dv/dv_bench2.py
vf() { echo "-GSU_LT=1 -GHD_W130=1 -GMU_NU=$2 -GFACE=$([ "$1" = W ] && echo 1 || echo 2)"; }
run() { # out-case env... -- args
  local c=$1; shift; local envs=(); while [ "$1" != "--" ]; do envs+=("$1"); shift; done; shift
  { echo "# case $c env ${envs[*]} args $* host $(hostname) $(date -Is) commit $(cat SOURCE_COMMIT 2>/dev/null) $(verilator --version)";
    env "${envs[@]}" python3 "$B" "$@"; echo "# exit $?"; } > "$R/$c.out" 2>&1
}
case $C in
P*) f=${C:1:1}; nu=${C#P?_}
  if [ "$nu" = 4 ]; then run "$C" X=0 -- a b c d e f g i j k m o n --vflags "$(vf $f $nu)" --work "$WORK/$C"
  else run "$C" X=0 -- a b c d e f g i j k --vflags "$(vf $f $nu)" --work "$WORK/$C"
       run "NEG_m_nu1_$f" X=0 -- m --vflags "$(vf $f $nu)" --work "$WORK/$C"
       run "NEG_o_nu1_$f" X=0 -- o --vflags "$(vf $f $nu)" --work "$WORK/$C"; fi ;;
H*) f=${C:1:1}; nu=${C#H?_}; run "$C" X=0 -- h --vflags "$(vf $f $nu)" --work "$WORK/$C" ;;
K14_*) f=${C#K14_}; run "NEG_$C" X=0 -- k --mut 14 --vflags "$(vf $f 4)" --work "$WORK/$C" ;;
AM*) m=${C:2:1}; f=${C#AM?_}; b=m; [ "$m" = 5 ] && b=o; [ "$m" = 7 ] && b=n
  run "NEG_${b}_am${m}_$f" DV2_AM_MUT=$m -- $b --vflags "$(vf $f 4)" --work "$WORK/$C" ;;
*) echo "unknown case $C"; exit 2 ;;
esac
