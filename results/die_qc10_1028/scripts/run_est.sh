cd /srv/opentallas-scratch2/claude/die-qc10-1028/est; T=/srv/opentallas-scratch2/claude/wt/die-qc9-1028/tools/die_plan
for v in "$@"; do set -- $v; b=${EST%.py}_$1_$2_$3_${4:-x}; python3 -I ${EST:-est_spine.py} $b.json ${KS:-0.281} $1 $2 $3 ${4:-} | tail -1; python3 -I cap_fixed_tree.py ${b}_tp.txt $b.json ${EXTRA:-} --out plan_$b.json > plan_$b.log 2>&1; echo -n "$b rc $? "; python3 -c "
import json,statistics as st
p=json.load(open('plan_$b.json'));s=p['summary'];X=p['crossings']
w=[c['p_up_ps']+c['p_dn_ps'] for c in X]
print({k:s[k] for k in ('tree_edges_clean','max_tree_depth','depth4','depth8','fail','max_path_ambiguous_cycles','worst_margin_lo_ps','worst_margin_hi_ps')}, 'amb',len(s['tree_edges_ambiguous']),'w med %.0f max %.0f'%(st.median(w),max(w)))"; done
