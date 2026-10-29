#!/bin/bash
set -euo pipefail
cd /srv/opentallas-scratch2/claude/codex-selector-1028
mkdir -p tie
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
pids=()
for m in 0 1;do
 (
  iverilog -g2012 -s tb_hbm_idx_selector_sel_eq -Ptb_hbm_idx_selector_sel_eq.SMUT=$m -Ptb_hbm_idx_selector_sel_eq.TIE_ONLY=1 -o tie/m$m.vvp simsrc2/ot_hbm_idx_selector_static_sel.sv simsrc2/ot_hbm_idx_selector_compact.sv simsrc2/ot_hbm_idx_compact_tree.sv simsrc2/reference.sv simsrc2/memory.v tiesrc/tb.sv > tie/build$m.log 2>&1
  set +e
  vvp tie/m$m.vvp > tie/run$m.log 2>&1
  rc=$?
  set -e
  if [ "$m" = 0 ];then test "$rc" = 0;grep -q "TB_SEL_EQ PASS" tie/run$m.log;else test "$rc" != 0;grep -q "TB_SEL_EQ FAIL" tie/run$m.log;fi
 ) &
 pids+=("$!")
done
rc=0
for p in "${pids[@]}";do wait "$p" || rc=1;done
test "$rc" = 0
echo SELECTOR_TIE_CONTROL_PASS
