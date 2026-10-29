#!/bin/bash
set -eu
cd /srv/opentallas-scratch2/claude/codex-s81-ce12-tag-1029
iverilog -g2012 -s tb -o tag rtl/ot_hdc_delay.sv rtl/ot_v41_kreg.sv rtl/ot_v41_bf16_lanes3.sv tb_tag_delay.sv
vvp tag > good.log
iverilog -g2012 -DS81_BF_TAG_MUTANT -s tb -o tag_mutant rtl/ot_hdc_delay.sv rtl/ot_v41_kreg.sv rtl/ot_v41_bf16_lanes3.sv tb_tag_delay.sv
if vvp tag_mutant > mutant.log 2>&1; then echo 'FAIL mutant escaped'; exit 1; fi
grep 'tag difference' mutant.log
cat good.log
