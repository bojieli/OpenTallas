#!/bin/bash
# S81 xrt event replay (DIE-S81-56/PLAN 11-04): xrt1+xrt3 signed RF-J views, bksel_c signed outline, c1x_C__t3 tap_radius_um 220.
#   delta_xrt_event_1104.sh PLAN_IN SIDE_IN OUTDIR      (cwd = repo root; writes OUTDIR/plan_f.json, OUTDIR/side_b.json)
set -e
PI=$1; SI=$2; O=$3; D=physical/die_plan/s81
python3 $D/delta_xrt_rfj_1104.py $PI $O/plan_x.json $SI $O/side_x.json xrt1 xrt3 > $O/delta.json
python3 $D/delta_bksel_c3_1104.py $O/plan_x.json $O/plan_b.json $O/side_x.json $O/side_b.json > $O/delta_b.json
python3 -c "
import sys,json;sys.path[:0]=['$D','tools/die_plan']
from plan_event_1104 import plan_text
p=json.load(open('$O/plan_b.json'))
ck=p['partition_types']['dsdv_slice_c1x_C__t3']['clock']; assert 'tap_radius_um' not in ck
ck['tap_radius_um']=220   # added_tap_recentre fixed 0 (no legal single move); clk_t21 reaches 219.7 um; COORD 17:4x accepted
open('$O/plan_f.json','w').write(plan_text(p))"
