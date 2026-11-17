#!/bin/bash
# FABLE-FIX-HEAD-CORRIDOR: reconcile on ONE plan: alloc_r4 (unchanged) with the prefix map (edges_g1) vs the tag map (edges_g3).
set -u; L=/srv/opentallas-scratch2/claude/head-die-r/nf15e_e10; F=/srv/opentallas-scratch2/claude/fable-fix-head-corridor; P=${1:?plan}; T=${2:?tag}; cd $L; mkdir -p $F/rec
for m in g1 g3; do
  s=$L/hr4/edges_g1.py; [ $m = g3 ] && s=$F/edges_g3.py
  python3 -I $s model/corridor_complete_plan.json $P model/corridor_complete_bit_edges.json $F/rec/edges_${T}_$m.json > /dev/null || exit 1
  ( python3 -I hr3/alloc_r4.py --plan $P --edges $F/rec/edges_${T}_$m.json --grant kit_rtl_final52/bootstrap/hd_lep0N/m8_grant.json --band 490 851.44 --out $F/rec/w_${T}_$m.json > $F/rec/a_${T}_$m.log 2>&1
    python3 -I -c "import json;s=json.load(open('$F/rec/w_${T}_$m.json'))['summary'];print('REC $T map=$m',json.dumps({k:s[k] for k in ('nets','unassigned','reach_bad','worst_full_rect','worst_mandatory')}))" ) &
done; wait; echo "REC_DONE plan $(sha256sum $P | cut -c1-16)"
