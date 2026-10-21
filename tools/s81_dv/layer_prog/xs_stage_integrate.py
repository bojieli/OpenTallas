#!/usr/bin/env python3
"""Compose physical stage/die/copy/hop identity from an exact static capacity map.

This does not reuse the obsolete Sxxx occupancy calendar as a physical124-stage
schedule. It emits the route choices and priced crossing/area terms the new
calendar must bind, and exposes resource-window qualification as incomplete.
"""
import argparse, collections, hashlib, json
from pathlib import Path


def integrate(m, digest, die_mm2, hop_ns):
    assert m['verdict']['all_pass'] and not m['verdict']['missing']
    stages=m['stages']; assert len(stages)==m['stages_count']==124
    covered=collections.Counter(); dense=[]; copies=[]
    for s in stages:
        assert s['capacity']['pass'] and s['capacity']['layout_identical_all'],s['stage']
        assert s['capacity']['dense_layer']==s['dense_layer'] and s['capacity']['experts']==s['n_experts']
        assert len(s['dies'])==m['rank_dies_per_stage']==4
        for layer,first,last in s['experts']: covered.update((layer,e) for e in range(first,last+1))
        if s['dense_layer'] is not None: dense.append(s['dense_layer'])
        if s['copy_b']: copies.append(s)
    assert set(covered)=={(l,e) for l in range(40) for e in range(384)} and set(covered.values())=={1}
    assert sorted(dense)==list(range(40))
    primary=sum(len(s['dies']) for s in stages)
    copy_dies=sum(len(s['dies']) for s in copies)
    assert len(copies)==8 and {s['dense_layer'] for s in copies}=={2,8,14,20,24,28,32,36}
    nodes=[{'stage':s['stage'],'dense_layer':s['dense_layer'],'experts':s['experts'],
            'copy_A_dies':[d+'.A' for d in s['dies']],
            'copy_B_dies':[d+'.B' for d in s['dies']] if s['copy_b'] else [],
            'calendar_rows':s['calendar_rows'],'capacity':s['capacity']} for s in stages]
    hops=[]
    for a,b in zip(stages,stages[1:]):
        choices=[[a['stage']+'.'+ca,b['stage']+'.'+cb] for ca in ('A','B') if ca=='A' or a['copy_b']
                 for cb in ('A','B') if cb=='A' or b['copy_b']]
        hops.append({'from':a['stage'],'to':b['stage'],'route_choices':choices,'latency_ns_model':hop_ns,
                     'resource_windows':'OWED new physical-stage MU calendar'})
    whole={s['stage'] for s in stages if any(l in (2,8,14,20,24,28,32,36) for l in s['layers'])}
    total=primary+copy_dies+52
    return {'schema':'opentallas.s81_dv.physical_stage_composition.v1','map_sha256':digest,
            'scope':'exact content and topology identity; latency/area model; MU windows NOT QUALIFIED',
            'stage_count':len(stages),'rank_dies_per_stage':4,'layer_dies':primary,
            'copy_B_policy':'map-declared eight dense attention owner stages, four rank dies each',
            'historical_copy_B_80_correction':'legacy compute.py charged8*round(388/40)=80; current map copy_b flags cover8*4=32. Old rows retained; this opt-in composition derives count from actual stage dies.',
            'copy_B_stages':[s['stage'] for s in copies],'copy_B_dies':copy_dies,
            'fixed_head_other_dies_model':52,'total_dies_map_policy_model':total,
            'old_628_projection_correction_dies':total-628,
            'whole_index_layer_content_alternative_model':{'stages':sorted(whole),'copy_B_dies':len(whole)*4,'total_dies':primary+52+len(whole)*4,'adopted':False},
            'die_area_mm2_input':die_mm2,'logic_area_mm2_model':round(total*die_mm2,3),
            'physical_stage_boundaries_per_pass':len(hops),'extra_boundaries_over_97':len(stages)-97,
            'crossing_ns_model':hop_ns,'added_token_latency_ns_model':round((len(stages)-97)*hop_ns,3),
            'ar_rate':'OWED new stage-resource occupancy model and calendar',
            'mtp_rate':'OWED new stage-resource occupancy model and calendar',
            'users_ar':'OWED; old46 not inherited','users_mtp':'OWED; old10 not inherited',
            'stages':nodes,'stage_hops':hops,
            'latency_user_route':[s['stage']+'.A' for s in stages],
            'next_required':['bind measured resource windows per physical stage','compile phase-q4 A/B assignments with zero collisions','bind HBM/index helper addresses to actual new stage IDs','recompose AR/MTP rates','behavioural token-chain verification']}


def main():
    p=argparse.ArgumentParser();p.add_argument('--map',required=True);p.add_argument('--out',required=True)
    p.add_argument('--die-mm2',type=float,default=799.21);p.add_argument('--hop-ns',type=float,default=377.6)
    a=p.parse_args();b=Path(a.map).read_bytes();r=integrate(json.loads(b),hashlib.sha256(b).hexdigest(),a.die_mm2,a.hop_ns)
    Path(a.out).write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({k:v for k,v in r.items() if k not in ('stages','stage_hops','latency_user_route')}))
if __name__=='__main__': main()
