#!/bin/bash
# DS85: run_type.sh + type_parse.py on every fetched type dir that has no type_clk.json yet, 12 in parallel.
W=/srv/opentallas-scratch2/claude/die-s81-85/clkdie
cd /
ls -d $W/types/*/ | grep -v test_ | while read d; do [ -s "$d/type_clk.json" ] || [ ! -s "$d/6_final.spef" ] || echo "$d"; done |
  xargs -P 12 -I{} bash -c "$W/scripts/run_type.sh {} && python3 -I $W/scripts/type_parse.py {}"
