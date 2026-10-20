#!/bin/bash
# closure-loop qfd_d2d_static_sf7w-sf7w-5f6301507 stage bench_xsf7_mut_c0_late attempt 2b1
set -o pipefail
ot_pick() { local p; for p in "$@"; do [ -e "$p" ] && { printf '%s\n' "$p"; return 0; }; done; echo "OT_FLOW_MISSING: none of $* exists on $(hostname)" >&2; return 1; }
export RUN=/srv/opentallas-scratch/claude/closure-loop/qfd_d2d_static_sf7w-sf7w-5f6301507-bench
export SRC=/srv/opentallas-scratch/claude/closure-loop/qfd_d2d_static_sf7w-sf7w-5f6301507-bench/bench_src_a2
export CL=/srv/opentallas-scratch/claude/closure-loop/qfd_d2d_static_sf7w-sf7w-5f6301507-bench/cl
export HOST=ot-epyc6
export NAME=qfd_d2d_static_sf7w_sf7w_5f6301507
export LABEL=qfd_d2d_static_sf7w_sf7w_5f6301507
export RAW_NAME=qfd_d2d_static_sf7w-sf7w-5f6301507
export BLOCK=qfd_d2d_static_ovl_sf7
export COMMIT=5f6301507f8c163a0534980e69869d864feb1a0e
export THREADS=4
export CL_PHASE=bench
export CL_LABEL_SUFFIX=''
export CL_STOP_AFTER=''
export OT_PG_JOB_STRICT=0
export OT_PG_STRICT=0
echo 0 > /proc/self/oom_score_adj 2>/dev/null || true
for _d in "$HOME/.local/opentallas-tools/verilator-5.050/bin" "$HOME/.local/opentallas-tools/yosys-0.68/bin"; do [ -d "$_d" ] && export PATH="$_d:$PATH"; done
[ -f /srv/opentallas-scratch/claude/closure-loop/qfd_d2d_static_sf7w-sf7w-5f6301507-bench/cl/calib.json ] || echo '{"calibrate": "disabled"}' > /srv/opentallas-scratch/claude/closure-loop/qfd_d2d_static_sf7w-sf7w-5f6301507-bench/cl/calib.json
[ -f /srv/opentallas-scratch/claude/closure-loop/qfd_d2d_static_sf7w-sf7w-5f6301507-bench/cl/calib.env ] && { set -a; . /srv/opentallas-scratch/claude/closure-loop/qfd_d2d_static_sf7w-sf7w-5f6301507-bench/cl/calib.env; set +a; }
exec 9>/srv/opentallas-scratch/claude/closure-loop/qfd_d2d_static_sf7w-sf7w-5f6301507-bench/bench_src_a2.lock || exit $?
flock 9 || exit $?
if [ ! -d /srv/opentallas-scratch/claude/closure-loop/qfd_d2d_static_sf7w-sf7w-5f6301507-bench/bench_src_a2 ]; then
  rm -rf /srv/opentallas-scratch/claude/closure-loop/qfd_d2d_static_sf7w-sf7w-5f6301507-bench/bench_src_a2.tmp
  if [ -n "$(cd /srv/opentallas-scratch/claude/closure-loop/qfd_d2d_static_sf7w-sf7w-5f6301507-bench/src && find . -type f -links +1 -perm 444 \( -name '*.lib' -o -name '*.lef' \) -print -quit)" ]; then
    mkdir /srv/opentallas-scratch/claude/closure-loop/qfd_d2d_static_sf7w-sf7w-5f6301507-bench/bench_src_a2.tmp || exit $?
    ( cd /srv/opentallas-scratch/claude/closure-loop/qfd_d2d_static_sf7w-sf7w-5f6301507-bench/src && find . ! \( -type f -links +1 -perm 444 \( -name '*.lib' -o -name '*.lef' \) \) -print0 | tar --null --no-recursion -T - -cf - ) | tar -xf - -C /srv/opentallas-scratch/claude/closure-loop/qfd_d2d_static_sf7w-sf7w-5f6301507-bench/bench_src_a2.tmp || exit $?
    ( cd /srv/opentallas-scratch/claude/closure-loop/qfd_d2d_static_sf7w-sf7w-5f6301507-bench/src && find . -type f -links +1 -perm 444 \( -name '*.lib' -o -name '*.lef' \) -print0 | xargs -0 -r sh -c 'cp -al --parents -t "$0" "$@" 2>/dev/null || cp -a --parents -t "$0" "$@"' /srv/opentallas-scratch/claude/closure-loop/qfd_d2d_static_sf7w-sf7w-5f6301507-bench/bench_src_a2.tmp ) || exit $?
  else
    cp -a --reflink=auto /srv/opentallas-scratch/claude/closure-loop/qfd_d2d_static_sf7w-sf7w-5f6301507-bench/src /srv/opentallas-scratch/claude/closure-loop/qfd_d2d_static_sf7w-sf7w-5f6301507-bench/bench_src_a2.tmp || exit $?
  fi
  mv /srv/opentallas-scratch/claude/closure-loop/qfd_d2d_static_sf7w-sf7w-5f6301507-bench/bench_src_a2.tmp /srv/opentallas-scratch/claude/closure-loop/qfd_d2d_static_sf7w-sf7w-5f6301507-bench/bench_src_a2 || exit $?
fi
flock -u 9; exec 9>&-
cd /srv/opentallas-scratch/claude/closure-loop/qfd_d2d_static_sf7w-sf7w-5f6301507-bench/bench_src_a2 || exit $?
XQ_PLAN=2,2,2,3,2,2/11,11,9,9,9,9,9 XQ_G='-GC_OVL=3' XQ_GEN_TXDP_EXPECT=PASS XQ_GEN_TXDP=9,3,1,10/21,4,3,3 bash rtl/test/qwen_split/run_xdie_exchange_sf7.sh /srv/opentallas-scratch/claude/closure-loop/qfd_d2d_static_sf7w-sf7w-5f6301507-bench/bench/xsf7_mut_c0_late pair_gen_txdp
