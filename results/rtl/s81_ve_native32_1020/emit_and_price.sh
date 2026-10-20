#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
python3 svc7_bound_graph.py mapped.json --top ot_s81sl_ve --name ot_s81sl_ve_native32 --out ve_native32_limit32.v --limit 32 --clock-port clk --incremental
python3 price_graph.py
