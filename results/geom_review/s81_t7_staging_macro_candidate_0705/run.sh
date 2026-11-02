#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
sha256sum staging.sv sram.v tb.sv > INPUTS.sha256
iverilog -g2012 -s tb -o sim staging.sv sram.v tb.sv > compile.log 2>&1
/usr/bin/time -v vvp sim > actual.log 2> time.log
