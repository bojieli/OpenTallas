#!/usr/bin/env bash
# FLEET-MESH-1: full ssh matrix (row = from, col = to) over fleet_hosts.tsv, run on localhost.
D=$(dirname "$(readlink -f "$0")"); H=$(grep -v '^#' "$D/fleet_hosts.tsv" | cut -f1 | xargs)
printf '| from \\ to |'; for d in $H; do printf ' %s |' "$d"; done; echo
printf '|---|'; for d in $H; do printf -- '---|'; done; echo
for s in $H; do
  line=$(timeout 150 ssh -n -o ControlPath=none -o ConnectTimeout=10 -o BatchMode=yes "$s" "for d in $H; do
    if [ \$d = $s ]; then printf ' self |'; continue; fi
    r=\$(timeout 20 ssh -n -o BatchMode=yes -o ConnectTimeout=10 \$d hostname 2>/dev/null) && printf ' OK %s |' \"\$r\" || printf ' FAIL |'; done") || line=" UNREACHABLE |"
  echo "| $s |$line"
done
