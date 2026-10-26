#!/bin/bash
# hier_check.sh W TILES_SV : yosys hierarchy -check of every module in TILES_SV; resolves missing modules from the
# die rtl roots (rtl, physical/qkd_astk_strip/macros, physical/asap7_memory_macros{,_v2}); fails on any unresolved module
# Necessary release checks are unbounded. Callers may deliberately bound a
# diagnostic with HIER_CHECK_TIMEOUT_SECONDS; zero explicitly means unbounded.
HIER_CHECK_TIMEOUT_SECONDS=${HIER_CHECK_TIMEOUT_SECONDS:-0}
case "$HIER_CHECK_TIMEOUT_SECONDS" in
  ''|*[!0-9]*) echo "FAIL: HIER_CHECK_TIMEOUT_SECONDS must be a nonnegative integer"; exit 2;;
esac
runner=()
[[ "$HIER_CHECK_TIMEOUT_SECONDS" =~ ^0+$ ]] || runner=(timeout "$HIER_CHECK_TIMEOUT_SECONDS")
W=$1; T=$2; cd "$W" || exit 2
FILES="$T ${EXTRA_FILES:-}"; tops=$(cat $T | grep -oP "^\s*module\s+\K\w+")
for it in $(seq 1 400); do
  ok=1
  for top in $tops; do
    status=0
    out=$("${runner[@]}" yosys -q -p "$(for f in $FILES; do echo -n "read_verilog -sv -defer -DSYNTHESIS $f; "; done) hierarchy -check -top $top" 2>&1) || status=$?
    echo "HIERARCHY_TOP top=$top iteration=$it exit=$status"
    [ -z "$out" ] || printf '%s\n' "$out"
    # Missing-module exit 1 may be resolved below. Every other tool failure,
    # including timeout 124, is terminal even if no ERROR text was emitted.
    if [ "$status" -ne 0 ] && [ "$status" -ne 1 ]; then
      echo "FAIL top $top (yosys exit $status)"; exit "$status"
    fi
    miss=$(echo "$out" | grep -oP "Module \`\\\\\K\w+(?=' referenced)" | head -1)
    if [ -n "$miss" ]; then
      f=$(grep -rlP "^\s*module\s+$miss\b" rtl physical/qkd_astk_strip/macros physical/asap7_memory_macros_v2 physical/asap7_memory_macros --include=*.sv --include=*.v 2>/dev/null | grep -v "/test/" | head -1)
      [ -z "$f" ] && { echo "UNRESOLVED $miss (top $top)"; exit 1; }
      echo "add $f for $miss"; FILES="$FILES $f"; ok=0; break
    elif [ "$status" -ne 0 ] || echo "$out" | grep -q ERROR; then
      echo "FAIL top $top (yosys exit $status)"
      [ "$status" -ne 0 ] && exit "$status"
      exit 1
    fi
  done
  [ $ok = 1 ] && { echo "hierarchy -check PASS: $(echo $tops | wc -w) tile modules, $(echo $FILES | wc -w) files"; exit 0; }
done
echo "FAIL: too many iterations"; exit 1
