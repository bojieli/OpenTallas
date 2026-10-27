import json,sys
sys.path.insert(0,'oneqc/tools/die_plan')
import schema, reset_tree as RT
raw=json.load(open('pd/physical/die_plan/qwen_compute/die_plan.json'))
P=schema.Plan(raw,'pd/physical/die_plan/qwen_compute/die_plan.json')
for tn,t in raw['partition_types'].items():
    g=[h for h in t.get('hard_cores',[]) if h.get('bound_group')]
    if not g: continue
    tree=RT.for_type(P,t.get('split_of') or tn)
    depth={r['q']:r['depth'] for r in tree['relays']}
    roles=tree.get('tap_roles',{})
    lt=RT.leaf_tap(P,t.get('split_of') or tn)
    tg={x['inst']:x for x in tree.get('core_resets',[])}
    out=[]
    for h in g:
        x=tg.get(h['inst'])
        if x is None: out.append((h['inst'],'NO_TARGET')); continue
        s=f"rst_n_t{lt}"; d=f"rst_n_t{x['tap']}"
        out.append((h['inst'],x['pin'],s,depth.get(s),d,depth.get(d),roles.get(lt,'mission'),roles.get(x['tap'],'mission'),'OK' if s in depth and depth.get(s)==depth.get(d) and roles.get(lt,'mission')==roles.get(x['tap'],'mission') else 'FAIL'))
    print(tn,out)
