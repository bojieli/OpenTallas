#!/bin/bash
# DIE-HEAD-91: one LEC of the TILE kit copy with the branch lec.py; $1 = name, $2 = netlist (inside kit), $3 = tie (1/0)
cd /
D=/srv/opentallas-scratch2/claude/die-head-91/tilelec
export OT_LEC_TAP_TIE=$3
exec python3 -I $D/tools/lec.py $D/kit --netlist $2 --out $D/out/$1 --mem 40 --jobs 4
