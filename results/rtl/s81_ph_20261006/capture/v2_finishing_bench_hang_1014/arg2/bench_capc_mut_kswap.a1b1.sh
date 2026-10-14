#!/bin/bash
# closure-loop dsfd_capt_x8_dual-v2-bc2c93f92-arg2 stage bench_capc_mut_kswap attempt 1b1
set -o pipefail
export RUN=/srv/opentallas/claude/closure-loop/dsfd_capt_x8_dual-v2-bc2c93f92-arg2
export SRC=/srv/opentallas/claude/closure-loop/dsfd_capt_x8_dual-v2-bc2c93f92-arg2/bench_src_a1
export CL=/srv/opentallas/claude/closure-loop/dsfd_capt_x8_dual-v2-bc2c93f92-arg2/cl
export HOST=ot-epyc1tb
export NAME=dsfd_capt_x8_dual_v2_bc2c93f92_arg2
export LABEL=dsfd_capt_x8_dual_v2_bc2c93f92_arg2
export RAW_NAME=dsfd_capt_x8_dual-v2-bc2c93f92-arg2
export BLOCK=dsfd_capt_x8_dual
export COMMIT=bc2c93f9283e5099cb77b06de663d27cfd5a3ff3
export THREADS=8
export CL_PHASE=bench
export CL_LABEL_SUFFIX=''
export CL_STOP_AFTER=''
echo 500 > /proc/self/oom_score_adj 2>/dev/null || true
for _d in "$HOME/.local/opentallas-tools/verilator-5.050/bin" "$HOME/.local/opentallas-tools/yosys-0.68/bin"; do [ -d "$_d" ] && export PATH="$_d:$PATH"; done
[ -f /srv/opentallas/claude/closure-loop/dsfd_capt_x8_dual-v2-bc2c93f92-arg2/cl/calib.json ] || echo '{"calibrate": "disabled"}' > /srv/opentallas/claude/closure-loop/dsfd_capt_x8_dual-v2-bc2c93f92-arg2/cl/calib.json
[ -f /srv/opentallas/claude/closure-loop/dsfd_capt_x8_dual-v2-bc2c93f92-arg2/cl/calib.env ] && { set -a; . /srv/opentallas/claude/closure-loop/dsfd_capt_x8_dual-v2-bc2c93f92-arg2/cl/calib.env; set +a; }
exec 9>/srv/opentallas/claude/closure-loop/dsfd_capt_x8_dual-v2-bc2c93f92-arg2/bench_src_a1.lock || exit $?
flock 9 || exit $?
if [ ! -d /srv/opentallas/claude/closure-loop/dsfd_capt_x8_dual-v2-bc2c93f92-arg2/bench_src_a1 ]; then
  rm -rf /srv/opentallas/claude/closure-loop/dsfd_capt_x8_dual-v2-bc2c93f92-arg2/bench_src_a1.tmp
  if [ -n "$(cd /srv/opentallas/claude/closure-loop/dsfd_capt_x8_dual-v2-bc2c93f92-arg2/src && find . -type f -links +1 -perm 444 \( -name '*.lib' -o -name '*.lef' \) -print -quit)" ]; then
    mkdir /srv/opentallas/claude/closure-loop/dsfd_capt_x8_dual-v2-bc2c93f92-arg2/bench_src_a1.tmp || exit $?
    ( cd /srv/opentallas/claude/closure-loop/dsfd_capt_x8_dual-v2-bc2c93f92-arg2/src && find . ! \( -type f -links +1 -perm 444 \( -name '*.lib' -o -name '*.lef' \) \) -print0 | tar --null --no-recursion -T - -cf - ) | tar -xf - -C /srv/opentallas/claude/closure-loop/dsfd_capt_x8_dual-v2-bc2c93f92-arg2/bench_src_a1.tmp || exit $?
    ( cd /srv/opentallas/claude/closure-loop/dsfd_capt_x8_dual-v2-bc2c93f92-arg2/src && find . -type f -links +1 -perm 444 \( -name '*.lib' -o -name '*.lef' \) -print0 | xargs -0 -r sh -c 'cp -al --parents -t "$0" "$@" 2>/dev/null || cp -a --parents -t "$0" "$@"' /srv/opentallas/claude/closure-loop/dsfd_capt_x8_dual-v2-bc2c93f92-arg2/bench_src_a1.tmp ) || exit $?
  else
    cp -a --reflink=auto /srv/opentallas/claude/closure-loop/dsfd_capt_x8_dual-v2-bc2c93f92-arg2/src /srv/opentallas/claude/closure-loop/dsfd_capt_x8_dual-v2-bc2c93f92-arg2/bench_src_a1.tmp || exit $?
  fi
  mv /srv/opentallas/claude/closure-loop/dsfd_capt_x8_dual-v2-bc2c93f92-arg2/bench_src_a1.tmp /srv/opentallas/claude/closure-loop/dsfd_capt_x8_dual-v2-bc2c93f92-arg2/bench_src_a1 || exit $?
fi
flock -u 9; exec 9>&-
cd /srv/opentallas/claude/closure-loop/dsfd_capt_x8_dual-v2-bc2c93f92-arg2/bench_src_a1 || exit $?
bash tools/s81_ph/capc_bench.sh /srv/opentallas/claude/closure-loop/dsfd_capt_x8_dual-v2-bc2c93f92-arg2/bench m1 'mix' S81PH_CAPC_MUT_KSWAP
