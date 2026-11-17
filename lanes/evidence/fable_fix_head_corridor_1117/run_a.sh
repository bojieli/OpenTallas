#!/bin/bash
# FABLE-FIX-HEAD-CORRIDOR: allocator + vertical access on an existing column run dir.  usage: run_a.sh RUN TAG JOG [alloc args]
set -u; L=/srv/opentallas-scratch2/claude/head-die-r/nf15e_e10; F=/srv/opentallas-scratch2/claude/fable-fix-head-corridor
RUN=${1:?run}; T=${2:?tag}; JOG=${3:-8.64}; shift 3; A=$F/$RUN; cd $L
python3 -I $F/alloc_r5.py --plan $A/plan.json --edges $A/edges.json --grant kit_rtl_final52/bootstrap/hd_lep0N/m8_grant.json --band 490 851.44 --columns $A/cols.json --jog $JOG --cut-step 2 --out $A/witness_$T.json "$@" > $A/alloc_$T.log 2>&1; echo "ALLOC_RC=$?"
python3 -I -c "import json;s=json.load(open('$A/witness_$T.json'))['summary'];print('ALLOC',json.dumps({k:s[k] for k in ('nets','assigned','unassigned','reach_bad','worst_full_rect','worst_mandatory','worst_witness','unpaired_column_q_nets','worst_jog_ratio','worst_ff_site_ratio','unassigned_by_source')}))"
python3 -I hr4/vert_access.py $A/plan.json $A/edges.json $A/witness_$T.json $A/access_$T.json > $A/access_$T.log; grep ACCESS_DONE $A/access_$T.log
echo "RUN_A_DONE plan $(sha256sum $A/plan.json | cut -c1-16)"
