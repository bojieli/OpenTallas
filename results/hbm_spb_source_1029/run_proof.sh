#!/bin/bash
set -euo pipefail
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
cd /srv/opentallas-scratch2/claude/codex-hbm-spb-source-1029
python3 source/results/hbm_spb_source_1029/prepare_proof.py actual_v3 proof
iverilog -g2012 -s tb -o proof/transport_tb proof/good/ot_hbm_spb0_regs.sv proof/good/reset_fixture.sv proof/wrong_reset.sv source/results/hbm_spb_source_1029/reset_models.sv source/results/hbm_spb_source_1029/tb_reset.sv
for mut in 0 1 2 3; do vvp proof/transport_tb +MUT=$mut; done
