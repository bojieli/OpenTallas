#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
/home/ubuntu/.local/opentallas-tools/yosys-0.68/bin/yosys -T -s census.ys > yosys.log 2>&1
