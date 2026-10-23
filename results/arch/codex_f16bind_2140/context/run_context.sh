#!/bin/bash
set -euo pipefail
python3 -I results/arch/codex_f16bind_2140/context/context_seq_bench.py --work "$PWD/context_run" --mut 0 --verilator verilator --jobs 2 > context_run.log 2>&1
cat context_run.log
