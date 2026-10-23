#!/bin/bash
set -eu
$HOME/.local/opentallas-tools/yosys-0.68/bin/yosys -Q -s wtn.ys > yosys.log 2>&1
python3 construct.py > construct.log 2>&1
cat construct.log
