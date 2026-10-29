#!/bin/bash
set -euo pipefail
cd /srv/opentallas-scratch2/claude/codex-selector-1028
mkdir -p sim
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
for m in 0 1 3;do
 iverilog -g2012 -s tb_hbm_idx_selector_sel_eq -Ptb_hbm_idx_selector_sel_eq.SMUT=$m -o sim/m$m.vvp simsrc/ot_hbm_idx_selector_static_sel.sv simsrc/ot_hbm_idx_selector_compact.sv simsrc/ot_hbm_idx_compact_tree.sv simsrc/reference.sv simsrc/memory.v simsrc/tb.sv > sim/build$m.log 2>&1
 set +e
 vvp sim/m$m.vvp > sim/run$m.log 2>&1
 rc=$?
 set -e
 if [ "$m" = 0 ];then test "$rc" = 0;grep -q "TB_SEL_EQ PASS" sim/run$m.log;else test "$rc" != 0;grep -q "TB_SEL_EQ FAIL" sim/run$m.log;fi
done
echo SELECTOR_FULL_SIM_PASS
