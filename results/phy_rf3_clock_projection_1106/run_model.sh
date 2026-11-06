#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch3/claude/codex-phy-rf3-clock-model-1106
cd "$R"
iverilog -g2012 -s tb -Ptb.MUT=0 -o positive.vvp tb.sv canonical_st.sv rtl/*.sv > build.log 2>&1
vvp positive.vvp > positive.log 2>&1
iverilog -g2012 -s tb -Ptb.MUT=1 -o mutant.vvp tb.sv canonical_st.sv rtl/*.sv > mutant_build.log 2>&1
set +e
vvp mutant.vvp > mutant.log 2>&1
rc=$?
set -e
test "$rc" = 1
grep -q RF3_LIVE_FAIL mutant.log
cat positive.log mutant.log
echo RF3_MODEL_PASS_MUTANT_CAUGHT
