#!/usr/bin/env bash
# MU-QWEN-HEAD benches (R4 qfd_dv_amax_mu, R3 qfd_sys_face_mu_user) on Verilator 5.050 (the closure daemon's version).
# Run from the repository root on a fleet host:  bash results/rtl/mu_qwen_1018/head/run_head.sh
# Each case writes runs/<case>.log; expected verdicts (PASS cases must print PASS, mutants / negative must print FAIL)
# are checked at the end into runs/summary.txt.
set -u
V=${OT_VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
H=results/rtl/mu_qwen_1018/head; R=$H/runs; B=${OT_HEAD_BUILD:-/tmp/mu_qwen_head_$$}
mkdir -p "$R" "$B"
"$V" --version > "$R/verilator_version.txt"
grep -q "wire t_bad = te && ((tp >= 3'd2 && tp != 3'd5)" rtl/qwen_split/qfd_sys_face.sv || { echo "qfd_sys_face t_bad moved" > "$R/summary.txt"; exit 1; }
AM="rtl/qwen_dv/mu/qfd_dv_amax_mu.sv $H/amax_today_ref.sv $H/tb_amax_mu.sv"
UE="rtl/qwen_split/mu/qfd_sys_face_mu_user.sv $H/tb_user_event.sv"
build() { # name top mut files...
  local n=$1 top=$2 mut=$3; shift 3
  "$V" --binary --timing -Wno-fatal -Wno-lint -Wno-style --top-module "$top" -GMUT=$mut -Mdir "$B/$n" -o sim "$@" > "$B/$n.build.log" 2>&1 \
    || { echo "BUILD FAIL $n"; cat "$B/$n.build.log"; return 1; }
}
run() { # case top mut plusargs files...
  local c=$1 top=$2 mut=$3 pa=$4; shift 4
  { echo "# case $c top $top MUT=$mut plusargs '$pa' host $(hostname) $(date -Is)"; echo "# sources: $*"; sha256sum "$@";
    build "$c" "$top" "$mut" "$@" && "$B/$c/sim" $pa; echo "# exit $?"; } > "$R/$c.log" 2>&1
}
run amax_pass_s1   tb_amax_mu 0 "+seed=1 +heads=150" $AM &
run amax_pass_s2   tb_amax_mu 0 "+seed=2 +heads=150" $AM &
run amax_pass_s3   tb_amax_mu 0 "+seed=3 +heads=150" $AM &
run amax_neg_clear tb_amax_mu 0 "+seed=1 +neg"       $AM &
run amax_mut1_ge     tb_amax_mu 1 "+seed=1" $AM &
run amax_mut2_xtalk  tb_amax_mu 2 "+seed=1" $AM &
run amax_mut3_clrall tb_amax_mu 3 "+seed=1" $AM &
run amax_mut4_emitu  tb_amax_mu 4 "+seed=1" $AM &
run user_pass_s1   tb_user_event 0 "+seed=1" $UE &
run user_pass_s2   tb_user_event 0 "+seed=2" $UE &
run user_mut1_late   tb_user_event 1 "+seed=1" $UE &
run user_mut2_nochk  tb_user_event 2 "+seed=1" $UE &
run user_mut3_nu1    tb_user_event 3 "+seed=1" $UE &
wait
rc=0; : > "$R/summary.txt"
for f in "$R"/*.log; do
  c=$(basename "$f" .log)
  case $c in *pass*) want=PASS;; *) want=FAIL;; esac
  if grep -qE "^TB_[A-Z_]+ $want " "$f"; then v=OK; else v=BAD; rc=1; fi
  echo "$c want=$want $v :: $(grep -E '^TB_[A-Z_]+ (PASS|FAIL)' "$f" | head -1)" >> "$R/summary.txt"
done
echo "overall rc=$rc" >> "$R/summary.txt"; cat "$R/summary.txt"
rm -rf "$B"
exit $rc
