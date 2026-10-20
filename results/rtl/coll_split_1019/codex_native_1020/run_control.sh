#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/../../../.."
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
export OT_BENCH_J=4
verilator --version
python3 tools/qwen_coll_tp8_static_bench.py --split --safe-fan32 --latu 66 --lats 391 --only 'reduce_8w_x16|fault_nan' --out control_eq
