#!/bin/bash
# usage: rs.sh PLANNAME [match]
cd /srv/opentallas-scratch2/claude/kw45/src_qc_s25_4e2764d237
M=${2:-_sc_}
nice -n 19 python3 -I -B tools/die_plan/route_supply.py /srv/opentallas-scratch2/claude/sc-refloor-1/planq/$1.json --die qwen_compute --repo . --match "$M" --grt-halving edge_outline --out /srv/opentallas-scratch2/claude/sc-refloor-1/rs/$1 > /srv/opentallas-scratch2/claude/sc-refloor-1/rs/$1.log 2>&1
echo "RSDONE $1 rc=$?"
