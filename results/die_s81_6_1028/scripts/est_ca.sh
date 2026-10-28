#!/bin/bash
# DIE-S81-6: price a synthetic est run dir with the unchanged shared tools (landed_phase_ocv main -> count_align_plan MR2)
D=${1:?dir}
WT=/srv/opentallas-scratch2/claude/wt/die-s81-5; O=/srv/opentallas-scratch2/claude/die-s81-5
MR=/srv/opentallas-scratch2/claude/die-s81-4/mr2/tools/die_plan
python3 $WT/tools/s81_head/landed_phase_ocv.py $O/plan_s5.json $D --tools $WT/tools/die_plan --out $D/lpo.json > $D/lpo.log 2>&1 || { echo LPO_FAIL; tail -5 $D/lpo.log; exit 1; }
grep corelat250 $D/lpo.log | cut -c1-200
for S in 1.0485 1.0552; do
  python3 $MR/count_align_plan.py $D/lpo.json --scale $S --out $D/ca_s$S.json > $D/ca_s$S.log 2>&1
  python3 -c "import json,sys; s=json.load(open('$D/ca_s$S.json'))['summary']; print('CA $S', {k:s[k] for k in ('crossings','depth4','depth8','fail','max_path_ambiguous_cycles','worst_margin_lo_ps','worst_margin_hi_ps','lat_total_vs_old3','max_tree_depth')})"
done
