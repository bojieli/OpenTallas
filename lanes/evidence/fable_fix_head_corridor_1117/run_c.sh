#!/bin/bash
# FABLE-FIX-HEAD-CORRIDOR: column form on a base-legal plan.  usage: run_c.sh RUN BASE_PLAN [W] [JOG] [KEEP_COMPACT] [extra alloc args]
set -u; L=/srv/opentallas-scratch2/claude/head-die-r/nf15e_e10; F=/srv/opentallas-scratch2/claude/fable-fix-head-corridor
RUN=${1:?run}; BP=${2:?base plan}; CW=${3:-10.8}; JOG=${4:-8.64}; KEEP=${5:-}; shift 5 2>/dev/null; A=$F/$RUN; [ ! -e $A ] || { echo "$A exists"; exit 79; }
mkdir -p $A; cd $L
python3 -I $F/edges_g3.py model/corridor_complete_plan.json $BP model/corridor_complete_bit_edges.json $A/edges_base.json | cut -c1-120 || exit 1
python3 -I $F/place_cols.py $BP $A/edges_base.json $A/plan.json $A/cols.json $A/place.json $CW $JOG "$KEEP" > $A/place.log 2>&1; prc=$?; tail -1 $A/place.log; echo "PLACE_RC=$prc"; [ $prc = 0 ] || [ $prc = 3 ] || exit 1
python3 -I $F/edges_g3.py model/corridor_complete_plan.json $A/plan.json model/corridor_complete_bit_edges.json $A/edges.json | cut -c1-120 || exit 1
python3 -I $F/alloc_r5.py --plan $A/plan.json --edges $A/edges.json --grant kit_rtl_final52/bootstrap/hd_lep0N/m8_grant.json --band 490 851.44 --columns $A/cols.json --jog $JOG --cut-step 2 --out $A/witness.json "$@" > $A/alloc.log 2>&1; echo "ALLOC_RC=$?"
python3 -I -c "import json;s=json.load(open('$A/witness.json'))['summary'];print('ALLOC',json.dumps({k:s[k] for k in ('nets','assigned','unassigned','reach_bad','worst_full_rect','worst_mandatory','worst_witness','unpaired_column_q_nets','worst_jog_ratio','worst_ff_site_ratio','unassigned_by_source')}))"
python3 -I hr4/vert_access.py $A/plan.json $A/edges.json $A/witness.json $A/access.json | grep ACCESS_DONE
echo "RUN_C_DONE plan $(sha256sum $A/plan.json | cut -c1-16)"
