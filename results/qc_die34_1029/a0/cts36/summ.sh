#!/bin/bash
# summarize CTS logs: delay buffers, macro tree depth, setup repair end, hold gate line
for f in "$@"; do
  echo "== $f"
  grep -h "clock_tree_synthesis -\|CTS-0036\|OT_HOLD_STRUCTURAL\|Path depth" "$f" | head -4
  grep -h "OT_HOLD_STRUCTURAL\|exit\|Error\|ERROR" "$f" | tail -3
  grep -hE "^ *final \||^ *[0-9]+\* *\|" "$f" | tail -1
done
