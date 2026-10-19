#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
iverilog -V >evidence/iverilog.version 2>&1
iverilog -g2012 -s tb_powerup -o powerup.vvp coupon.sv tb_powerup.sv >evidence/powerup_build.log 2>&1
vvp powerup.vvp >evidence/powerup.log 2>&1
cat evidence/powerup.log
