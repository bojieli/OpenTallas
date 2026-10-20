#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
docker run --rm --memory=32g --memory-swap=32g -v "$PWD:/work" -w /work -e OT_KEEP_PIN_REGS=1 -e DESIGN_NAME=native_mu_top -e OT_RST_LAND=1 -e OT_RST_LAND_STAGES=2 -e OT_PIN_REGS_RESET_PORTS=rst_n -e OT_PIN_REGS_CLOCK=clk openroad/orfs:latest bash -lc "set -e; source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 prepare_native.py $1; yosys -l native4_$1/yosys.log -s native4_$1/synth.ys; python3 src/tools/textbook_lint.py check --netlist native4_$1/mapped.v --top native_mu_top --out native4_$1/census.json --mode refuse --refuse-checks high_fanout --set hf_report=32 hf_max=32 hf_port_refuse=32 hf_reset_refuse=32 hf_refuse=32 reach_um=405"
