#!/bin/bash
# usage: kit.sh <kit dirs...>  — summary of a kit state
for k in "$@"; do
  echo "=== $k"
  [ -d "$k" ] || { echo MISSING; continue; }
  ls "$k" | grep -E '^(DO_NOT_COUNT|FAILED|SUPERSEDED|STOP|HOLD_.*|ROUTE_STOP|FORM.*|.*\.done)$' | tr '\n' ' '; echo
  rd=$(ls -d "$k"/run/results/asap7/*/base 2>/dev/null | head -1)
  [ -n "$rd" ] && ls -t --time-style=+%m-%d_%H:%M -l "$rd" | grep -E '\.odb|\.v$' | head -3 | awk '{print $6,$7,$5}'
  ld=$(ls -d "$k"/run/logs/asap7/*/base 2>/dev/null | head -1)
  if [ -n "$ld" ]; then
    l=$(ls -t "$ld"/*.log | head -1); echo "latest log: $(basename $l) $(date -r $l +%m-%d_%H:%M)"; tail -3 "$l" | cut -c1-200
    g="$ld/5_1_grt.log"; [ -f "$g" ] && { grep -E 'Total overflow|GRT-0118|GRT-0116|overflow:|Routing resources' "$g" | tail -3 | cut -c1-160; }
    d="$ld/5_2_route.log"; [ -f "$d" ] && grep -E 'Completing|violations|Number of violations' "$d" | tail -2 | cut -c1-160
  fi
  for f in "$k"/lec/lec.json "$k"/signoff/signoff.json; do
    [ -f "$f" ] && { echo "$f $(date -r "$f" +%m-%d_%H:%M)"; python3 -I - "$f" <<'P'
import json,sys
d=json.load(open(sys.argv[1]))
print({k:d.get(k) for k in ('verdict','status','equivalent','signed','wns_tt','tns_tt') if k in d}, str(d.get('stats') or d.get('summary') or '')[:300])
P
    }
  done
done
