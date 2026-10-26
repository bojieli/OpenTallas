#!/bin/bash
set -euo pipefail
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
cd "$(dirname "$0")"
yosys -V > version.log
yosys -Q -p 'read_verilog -sv -lib bb.v; read_verilog -sv good.v; hierarchy -check -top top; stat' > good.log 2>&1
set +e
yosys -Q -p 'read_verilog -sv -lib bb.v; read_verilog -sv bad.v; hierarchy -check -top top; stat' > bad.log 2>&1
rc=$?
set -e
if [ "$rc" -eq 0 ]; then echo 'FAIL unknown parameter was accepted'; exit 1; fi
grep -iE 'parameter.*(not|unknown|undeclared)|does not have.*parameter' bad.log
printf 'CLASSIC BB PASS named overrides accepted; unknown-param control rejected rc=%s\n' "$rc"
