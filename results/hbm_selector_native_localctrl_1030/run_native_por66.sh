#!/bin/bash
set -eu
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
for m in 0 5; do
  iverilog -g2012 -s tb_sel_localctrl -Ptb_sel_localctrl.NMUT=$m -Ptb_sel_localctrl.NCYC=1600 -Ptb_sel_localctrl.NRST=4 -o sim$m.vvp ot_hbm_idx_selector_static_sel.sv old_sel.sv ot_hbm_idx_selector_compact.sv ot_hbm_idx_compact_tree.sv ot_sram_1r1w_256x256_m2_r2c2.v tb_native_por66.sv > build$m.log 2>&1
  set +e
  vvp sim$m.vvp > run$m.log 2>&1
  rc=$?
  set -e
  echo $rc > run$m.rc
  tail -8 run$m.log
  if [ $m = 0 ]; then [ $rc = 0 ] && grep -q 'TB_SEL_LOCALCTRL PASS' run$m.log; else [ $rc != 0 ] && grep -q 'TB_SEL_LOCALCTRL FAIL' run$m.log; fi
done
