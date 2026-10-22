#!/bin/bash
# QW-ORPHANS obs_fault protocol: M=0 positive (obs_fault=0, full paired-wrapper compare), M=40 causal negative.
set -u
Q=/srv/opentallas-scratch/claude/qw-sysface4-1020; M=$1
export PATH="$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH"
cd $Q/src6b
OUT=../p6b_m$M
bash rtl/test/qwen_split/run_sys_face_native32_protocol.sh $OUT protocol6 $M; RC=$?
if [ "$M" = 40 ]; then
  if grep -q 'SYSFACE32_WRAPPER_MISMATCH port=fault ' $OUT/run.log && ! grep -q 'SYSFACE32_WRAPPER_MISMATCH port=[^f]' $OUT/run.log; then echo OBS_NEG_PASS_CAUGHT; grep -m1 'SYSFACE32_WRAPPER_MISMATCH' $OUT/run.log; exit 0; else echo OBS_NEG_FAIL_NOT_CAUGHT; tail -5 $OUT/run.log; exit 1; fi
fi
echo POS_RC=$RC; tail -4 $OUT/run.log; exit $RC
