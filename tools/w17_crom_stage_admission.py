"""Join actual local images/calendar and fresh typed physical-slot failures."""
import argparse,hashlib,json,subprocess
from decimal import Decimal

def build():
    pins={}
    def load(n,ref,path):
        b=subprocess.check_output(['git','show',ref+':'+path]);pins[n]=dict(commit=ref,path=path,sha256=hashlib.sha256(b).hexdigest());return json.loads(b)
    price=load('fresh_typed','4276c2587','results/uarch/w10_crom_actual_stage_budget_r1/budget.json')
    models={b:load('model'+str(b),'3977c3392',f'results/quality/w16_engram_initializer_20261001/stage_local{b}.json') for b in (6,9,16)}
    old=load('preserved45','3977c3392','results/quality/w16_engram_initializer_20261001/stage_local45_rows.json')
    rows=[]
    for c in price['cases']:
        b=c['parameter_banks'];cr=c['credits'];expected=(49 if b==45 else models[b]['regular_element']['total_macros_per_home'])
        assert c['macro_count']==expected
        assert Decimal(c['exclusive_SU_slot_area_deficit_mm2'])>0 and not c['physical_admission']
        if b!=45:
            total=sum(d['finite_fill_and_reverse_credit_ticks'] for s in models[b]['stages'] for cmd in s['commands'] for d in cmd['finite_services'] if d['credits']==cr)
            assert Decimal(c['finite_coefficient_only_calendar_us'])==Decimal(total)/3600
        assert c['fit_verdict']=='FAIL_CHOSEN_RETAINED_STAGING_RESERVATION'
        rows.append(dict(parameter_banks=b,credits=cr,macro_count=expected,
            fresh_conditional_area_mm2=c['fresh_declared_reservation']['conditional_cell_plus_macro_area_mm2'],
            exclusive_SU_slot_area_deficit_mm2=c['exclusive_SU_slot_area_deficit_mm2'],
            coefficient_only_calendar_us=c['finite_coefficient_only_calendar_us'],
            physical_slot_verdict=c['fit_verdict'],hardware_admission=False))
    assert len(rows)==12 and old['max_regular_rows_per_bank']==250
    return dict(schema='opentallas.CROM-stage-local-admission.v1',source_pins=pins,cases=rows,
        selected_adopted_point=None,fastest_coefficient_only_banks=45,
        actual_whole_power_W=None,actual_whole_margin_W=None,full_token_cycles=None,
        admission_verdict='FAIL_ALL12_CURRENT_SU_SLOT_CONSTRUCTIONS_AND_SOURCE_SERVICE_GATES',
        no_proportional_power_transfer=True,no_undersized_instance_credit=True,
        exact_relocation='3977 scalar request/fill and retained value validity checks; compiler89a653 separately diagnostic NOT_RUNNABLE',
        next_minimum_corrections=['source-priced135existing1024x72 alternative including90extra clock endpoints and all captures',
            'or explicit relocated coefficienthome preserving retainedSU/HC/currentdie geometry with pricedroutes',
            'complete actualcatalog and consumer service deadlines','L1 actualsource provenance'],
        failures_are_chosen_constructions_not_physical_minimum=True,
        hardware_admission=False,jobs_launched=0,checkpoint_reads=0)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args()
    with open(a.output,'w') as f:json.dump(build(),f,sort_keys=True,indent=2);f.write('\n')
