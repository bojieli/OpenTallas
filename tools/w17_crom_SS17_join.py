"""Current sourceSS17 calendar + fresh physical inventory admission authority."""
import argparse,hashlib,json,subprocess
from decimal import Decimal as D

def build():
    pins={}
    def load(n,ref,path):
        raw=subprocess.check_output(['git','show',ref+':'+path]);pins[n]=dict(commit=ref,path=path,sha256=hashlib.sha256(raw).hexdigest());return json.loads(raw)
    typed=load('typed17','db6ae8e09','results/uarch/w10_crom_ss_route17_budget_r1/budget.json')
    models={b:load('model'+str(b),'30ee8b637',f'results/quality/w16_engram_initializer_20261001/stage_local{b}_SS17.json') for b in (6,9,16)}
    m45=load('model45','30ee8b637','results/quality/w16_engram_initializer_20261001/stage_local45_rows_SS17.json')
    for m in list(models.values())+[m45]:assert m['SS_route_basis']['stages_each_direction']==17
    rows=[]
    for case in typed['cases']:
        b=case['parameter_banks'];cr=case['credits']
        if b==45:
            ticks=sum(next(d for d in c['deliveries'] if d['credits']==cr)['cold_fill_plus_credit_ticks'] for s in m45['stages'] for c in s['commands'])
        else:
            ticks=sum(d['finite_fill_and_reverse_credit_ticks'] for s in models[b]['stages'] for c in s['commands'] for d in c['finite_services'] if d['credits']==cr)
        assert case['extra_pipeline_FF_vs11']==6912
        assert D(case['exclusive_SU_slot_area_deficit_mm2'])>0
        rows.append(dict(parameter_banks=b,credits=cr,source_bound_coefficient_only_ticks=ticks,
            source_bound_coefficient_only_us=str(D(ticks)/3600),
            exclusive_SU_slot_area_deficit_mm2=case['exclusive_SU_slot_area_deficit_mm2'],
            FF_by_role=case['FF_by_role'],fresh_declared_reservation=case['fresh_declared_reservation'],
            fit_verdict='FAIL_CHOSEN_CURRENT_SU_SLOT_CONSTRUCTION',hardware_admission=False))
    assert len(rows)==12
    return dict(schema='opentallas.CROM-SS17-current-admission.v1',source_pins=pins,cases=rows,
        small_macro_cases=typed['small_macro_alternative_cases'],
        small_macro_actual_service_calendar=None,
        route_stages_each_direction=17,old11_history_preserved_not_qualified=True,
        actual1152bit_bus_SSreach_and_tracks_bound=False,actual_boundary_CDC_state_and_cycles_bound=False,
        actual_whole_power_W=None,actual_whole_margin_W=None,full_token_cycles=None,
        verdict='FAIL_ALL_CURRENT_SLOT_CONSTRUCTIONS_PLUS_IMAGE_CATALOG_CDC_AND_CONTEXT_GATES',
        source_L1_invalid=True,physical_catalog_published=False,
        single_gamma_lifetime_candidate_not_automatically_applied=True,
        selected_adopted_point=None,hardware_admission=False,jobs_launched=0,checkpoint_reads=0)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args()
    with open(a.output,'w') as f:json.dump(build(),f,sort_keys=True,indent=2);f.write('\n')
