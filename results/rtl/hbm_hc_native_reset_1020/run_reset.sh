#!/bin/bash
set -euo pipefail
iverilog -V 2>&1 | head -1 || true
iverilog -g2012 -s tb_reset -o reset.vvp tb_reset.sv reset_local_only.sv ot_rst_relay.sv
vvp reset.vvp | tee reset_protocol.log
