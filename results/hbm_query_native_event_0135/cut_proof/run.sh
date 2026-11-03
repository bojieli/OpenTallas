#!/bin/bash
set -euo pipefail
cd /srv/opentallas-scratch2/claude/codex-hbm-query-cut-proof-0155
iverilog -g2012 -s tb -o cut.vvp ot_dp_st.sv cut_miter.sv
vvp cut.vvp | tee proof.log
