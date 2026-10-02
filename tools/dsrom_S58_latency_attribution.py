#!/usr/bin/env python3
"""Trace only reference41 and the sharedS58 analytical DAG, no count sweep/build."""
import argparse
import collections
import copy
import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PIN='4c8b7f2d8e246bd09250051fc8f7cb3e3340f574'
OPTIONS='results/uarch/dsrom_4096_comparable_capacity_20261002/partition_token_options.json'

def build():
    sys.path.insert(0,str(ROOT/'tools'))
    import uarch_model as u
    pins={}
    for path in ['tools/uarch_model.py','tools/decode_critical_path.py',OPTIONS]:
        raw=subprocess.check_output(['git','show',PIN+':'+path],cwd=ROOT)
        assert (ROOT/path).read_bytes()==raw
        pins[PIN+':'+path]=hashlib.sha256(raw).hexdigest()
    options=json.loads((ROOT/OPTIONS).read_text())
    saved=copy.deepcopy(u.PRESETS['proposal']);rows=[]
    try:
        for S in [41,58]:
            opt=next(r for r in options['priced_options'] if r['capacity']['stages']==S)
            b=opt['capacity']['BF16_pairs_per_die']
            u.PRESETS['proposal']['bf16_stripe_macros']=2*b
            plan=u.cons_stage_plan(S)
            with u._cons_clock(u.PRODUCT_CLOCK_HZ),u._cons_stages(S):
                d=copy.deepcopy(u.PRESETS['proposal']);d['vmh_block']=u.PRODUCT_HUB
                d['macros']=round(u.BASE['macros']*plan['busiest_macros']/u.cons_stage_plan(28)['busiest_macros'])
                priced,g=u._v41_graph(d,1)
                T=u._cons_adjust(g,1,priced['clock_hz'],'columns',u.FIELD_CONCURRENCY,
                    dict(u.SOFTPLUS_FIX,**u.W11_STREAM_SS,**u.PLUS_LAT),(.9e9,'w18'),None,8,True,d,u.PRODUCT_SERIAL,u.DIE_SHRUNK_INTERIM,u.VMC_FUSED)
            sink=next(n for n in g.nodes if n.endswith('token.return'))
            path=g.path(sink);groups=collections.Counter();cats=collections.Counter();events=[]
            for name in path:
                nd=g.nodes[name];a=nd.get('_uarch')
                group='field_'+str(a.get('fmt','unknown')) if a else ('hop' if nd['kind']=='hop' else nd['kind'])
                contribution=sum(g.contrib[name].values())*1e6
                groups[group]+=contribution
                for k,v in g.contrib[name].items():cats[k]+=v*1e6
                events.append(dict(node=name,kind=nd['kind'],group=group,issue_us=nd['issue']*1e6,depth_us=nd['depth']*1e6,exposed_us=contribution,
                    contribution_us={k:v*1e6 for k,v in g.contrib[name].items()},field_terms=a,description=nd['desc'],deps=nd['deps']))
            assert math.isclose(sum(groups.values()),T*1e6,abs_tol=1e-7)
            published=1e6/round(1/T,1)
            assert math.isclose(published,opt['retained_analytical_full_token_us'],abs_tol=1e-8)
            rows.append(dict(stages=S,BF_pairs=b,source_model_macros=d['macros'],raw_unrounded_token_us=T*1e6,published_rounded_rate_reciprocal_us=published,
                published_pipeline_hops_us=opt['retained_analytical_pipeline_hops_us'],critical_path_contribution_by_group_us=dict(groups),critical_path_contribution_by_category_us=dict(cats),critical_path=events))
    finally:
        u.PRESETS['proposal'].clear();u.PRESETS['proposal'].update(saved)
    old,new=rows
    group_delta={k:new['critical_path_contribution_by_group_us'].get(k,0)-old['critical_path_contribution_by_group_us'].get(k,0) for k in sorted(set(old['critical_path_contribution_by_group_us'])|set(new['critical_path_contribution_by_group_us']))}
    cat_delta={k:new['critical_path_contribution_by_category_us'].get(k,0)-old['critical_path_contribution_by_category_us'].get(k,0) for k in sorted(set(old['critical_path_contribution_by_category_us'])|set(new['critical_path_contribution_by_category_us']))}
    old_events={r['node']:r for r in old['critical_path']}
    operator_deltas=collections.Counter();changed_field=[]
    for r in new['critical_path']:
        prior=old_events.get(r['node']);a=r['field_terms']
        if prior and a:
            delta=r['exposed_us']-prior['exposed_us'];operator_deltas[a['key']]+=delta
            if abs(delta)>1e-10:
                changed_field.append(dict(node=r['node'],operator_key=a['key'],exposed_delta_us=delta,
                    old_t_read=prior['field_terms']['t_read'],new_t_read=a['t_read'],
                    old_t_x=prior['field_terms']['t_x'],new_t_x=a['t_x'],
                    old_t_ret=prior['field_terms']['t_ret'],new_t_ret=a['t_ret'],
                    old_t_mac=prior['field_terms']['t_mac'],new_t_mac=a['t_mac']))
    pub_delta=new['published_rounded_rate_reciprocal_us']-old['published_rounded_rate_reciprocal_us']
    hop=new['published_pipeline_hops_us']-old['published_pipeline_hops_us']
    return dict(schema='opentallas.DSROM.S58.latency-attribution.v1',candidate_id='DS4096-TP4-S58-PAIR1',source_pins=pins,rows=rows,
        published_total_delta_us=pub_delta,published_hop_delta_us=hop,published_nonhop_remainder_us=pub_delta-hop,
        unrounded_DAG_delta_us=new['raw_unrounded_token_us']-old['raw_unrounded_token_us'],
        rounded_rate_publication_residual_us=pub_delta-(new['raw_unrounded_token_us']-old['raw_unrounded_token_us']),
        critical_path_field_operator_deltas_us=dict(operator_deltas),changed_field_events=changed_field,
        head_scope_risk=dict(retained_head_dies=8,global_BF_stripe_setting_applies_to_head=True,
            lm_head_t_read_cycles_5120_to7360=True,lm_head_exposed_delta_us=operator_deltas['lm_head'],
            changed_head_BF_seat_capacity_not_just_added_stage_hops=True,
            actual_head_residence_under_S58_source_bound=False,
            required_join='Bind per-roleBF inventory; if head stays unchanged do not silently reduce its seats via globalBF stripe setting. Current390.061us includes this head change; price role-specific source calendar before adoption.'),
        critical_path_group_deltas_us=group_delta,critical_path_category_deltas_us=cat_delta,
        attribution_scope='Differences of actual longest-path exposed contributions, not sum of all broadcasts, node depths or service work. Path changes and overlap included. Retained historical calibrated assumptions remain; no connected current RTL timing credit.',
        price_matvec_rule='Reduced field macros/BF stripe seats change source t_read/t_x/t_ret/t_mac and max-bound issue; _cons_adjust retains8*element_stages recurrence floor. Recompiled stage/substage DAG changes overlap. SameTP4 golden compute/order; no reduction reassociation.',
        capacity_verdict='FAIL_S58_CORRECTED_SERVICE_CAPACITY_SCREEN',count_selected=False,new_counts_swept=0,RTL_PnR=False,rate_claim=False)
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=build()
    if a.output.exists():raise ValueError('Refusing overwrite')
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2,sort_keys=True)+'\n')
    print(json.dumps({k:v for k,v in r.items() if k not in ['rows','source_pins','changed_field_events']}))
