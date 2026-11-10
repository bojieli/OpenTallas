#!/bin/bash
# DS85: run_type_cts.sh + type_parse.py on every fetched types_cts dir without type_clk.json, 12 in parallel.
W=/srv/opentallas-scratch2/claude/die-s81-85/clkdie
cd /
ls -d $W/types_cts/*/ | while read d; do [ -s "$d/type_clk.json" ] || [ ! -s "$d/source.json" ] || echo "$d"; done |
  xargs -P 12 -I{} bash -c "$W/scripts/run_type_cts.sh {} && python3 -I $W/scripts/type_parse.py {}"
