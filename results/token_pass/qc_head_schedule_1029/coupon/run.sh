#!/bin/bash
set -eu
iverilog -g2012 -s tb -o sim dut_m0.sv qfd_mu_head_context_tx_lctx32.sv qfd_mu_head_context_tx_lctx32_helpers.sv tb.sv > compile.log 2>&1
for mode in 0 1 2; do
  vvp sim +MODE=$mode > mode$mode.log 2>&1
  if vvp sim +MODE=$mode +MUT=1 > mode${mode}_early.log 2>&1; then exit 3; fi
done
if vvp sim +MUT=2 > wrong_token.log 2>&1; then exit 4; fi
echo PASS
