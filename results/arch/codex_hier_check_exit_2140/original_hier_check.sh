#!/bin/bash
# hier_check.sh W TILES_SV : yosys hierarchy -check of every module in TILES_SV; resolves missing modules from the
# die rtl roots (rtl, physical/qkd_astk_strip/macros, physical/asap7_memory_macros{,_v2}); fails on any unresolved module
W=$1; T=$2; cd "$W" || exit 2
FILES="$T ${EXTRA_FILES:-}"; tops=$(cat $T | grep -oP "^\s*module\s+\K\w+")
for it in $(seq 1 400); do
  ok=1
  for top in $tops; do
    out=$(timeout 600 yosys -q -p "$(for f in $FILES; do echo -n "read_verilog -sv -defer -DSYNTHESIS $f; "; done) hierarchy -check -top $top" 2>&1)
    miss=$(echo "$out" | grep -oP "Module \`\\\\\K\w+(?=' referenced)" | head -1)
    if [ -n "$miss" ]; then
      f=$(grep -rlP "^\s*module\s+$miss\b" rtl physical/qkd_astk_strip/macros physical/asap7_memory_macros_v2 physical/asap7_memory_macros --include=*.sv --include=*.v 2>/dev/null | grep -v "/test/" | head -1)
      [ -z "$f" ] && { echo "UNRESOLVED $miss (top $top)"; exit 1; }
      echo "add $f for $miss"; FILES="$FILES $f"; ok=0; break
    elif echo "$out" | grep -q ERROR; then echo "$out" | tail -5; echo "FAIL top $top"; exit 1
    fi
  done
  [ $ok = 1 ] && { echo "hierarchy -check PASS: $(echo $tops | wc -w) tile modules, $(echo $FILES | wc -w) files"; exit 0; }
done
echo "FAIL: too many iterations"; exit 1
