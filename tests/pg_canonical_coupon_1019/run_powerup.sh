#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
iverilog -V >evidence_v2/iverilog.version 2>&1
iverilog -g2012 -s tb_powerup -o powerup.vvp coupon.sv tb_powerup.sv >evidence_v2/powerup_build.log 2>&1
vvp powerup.vvp >evidence_v2/powerup.log 2>&1
cat evidence_v2/powerup.log
