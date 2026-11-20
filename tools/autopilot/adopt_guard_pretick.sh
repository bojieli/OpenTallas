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
  # FLOW-FIX-2045 (FABLE-FLOW-1949 class 6: 24 identical alerts in 2 h): one ALERT per distinct line per hour (stamp file per line hash)
  S="$AP/.adopt_alert_seen"; mkdir -p "$S"; find "$S" -type f -mmin +180 -delete 2>/dev/null
  printf '%s\n' "$out" | grep -E 'MISMATCH|MISSING|FIX' | while read -r l; do
    h=$(printf '%s' "$l" | md5sum | cut -c1-16)
    if [ -z "$(find "$S/$h" -mmin -60 2>/dev/null)" ]; then : > "$S/$h"; printf '%s AUTOPILOT: ALERT %s\n' "$(date '+%Y-%m-%d %H:%M:%S %Z')" "$l" >> "$AP/log.txt"; fi
  done
else rm -f "$AP/ADOPT-GUARD-FAILED"; fi
exit 0
