#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
export VERILATOR="$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator"
export VL_JOBS=4 HDC_V41_ARITH=chunk8
exec /usr/bin/time -v python3 ./run_native.py
