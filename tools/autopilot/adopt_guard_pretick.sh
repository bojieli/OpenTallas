#!/bin/bash
# KIT-OPS-6 11-14 (COORD r32 (4)): pre-tick ADOPT-GUARD plan_sha256 check for every die.  Never blocks the tick (exit 0); a mismatch writes
# one ALERT line per die to the autopilot log and autopilot/ADOPT-GUARD-FAILED (removed when all dies pass), with the exact fix.
AP=$HOME/coord/autopilot; G=$HOME/OpenTallas/tools/autopilot/adopt_guard.py
out=""; for d in qwen_kvsys s81 s81_head qwen_compute hbm; do
  o=$(timeout 90 python3 -I "$G" "$d" --plan-only 2>&1); rc=$?
  [ $rc -ne 0 ] && out="$out$o"$'\n'
done
if [ -n "$out" ]; then
  printf '%s\n' "$out" > "$AP/ADOPT-GUARD-FAILED"
  printf '%s\n' "$out" | grep -E 'MISMATCH|MISSING|FIX' | while read -r l; do printf '%s AUTOPILOT: ALERT %s\n' "$(date '+%Y-%m-%d %H:%M:%S %Z')" "$l" >> "$AP/log.txt"; done
else rm -f "$AP/ADOPT-GUARD-FAILED"; fi
exit 0
