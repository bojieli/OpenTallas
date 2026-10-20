#!/bin/bash
set -euo pipefail
cd /work/src
python3 tools/textbook_trace.py check --netlist /work/native7/mapped.v --top qfd_tt_ctlm_dv_np_lp --out /work/native7/trace.json > /work/native7/trace.stdout 2>&1 || true
python3 depth7.py
