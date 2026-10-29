#!/bin/bash
set -euo pipefail
cd /srv/opentallas-scratch2/claude/codex-selector-1028/procsplit
pids=()
for case in full tie threshold fault;do
 (
  m=0;t=0
  case "$case" in tie)t=1;;threshold)m=1;t=1;;fault)m=3;;esac
  /usr/bin/iverilog -g2012 -s tb_hbm_idx_selector_sel_eq -Ptb_hbm_idx_selector_sel_eq.SMUT=$m -Ptb_hbm_idx_selector_sel_eq.TIE_ONLY=$t -o "$case.vvp" src/*.sv src/memory.v > "$case.build.log" 2>&1
  set +e
  /usr/bin/vvp "$case.vvp" > "$case.run.log" 2>&1
  rc=$?
  set -e
  if [[ $m = 0 ]];then test $rc = 0;grep -q 'TB_SEL_EQ PASS' "$case.run.log";else test $rc != 0;grep -q 'TB_SEL_EQ FAIL' "$case.run.log";fi
 ) &
 pids+=("$!")
done
rc=0
for p in "${pids[@]}";do wait "$p" || rc=1;done
exit "$rc"
