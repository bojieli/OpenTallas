#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
"$V" --binary --timing --top-module tb -j 2 -Wno-fatal -Wno-lint -Wno-style --Mdir obj -f sources.f >build.log 2>&1
