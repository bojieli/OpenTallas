"""Additive corrected service pin; retain historical compiler proof and failures."""
import argparse
import json
from decimal import Decimal
from pathlib import Path
import w11_dsrom_stage_crom_union as U

PREFIX='results/quality/w16_engram_initializer_20261001/'
NEW='30ee8b637cb3de96a89afbeede43613b232cdfc8'
OLD='3977c33920751cbd40db970ae3d87a7046e0d658'
RECEIPT=('89a6538a8','results/uarch/w11_stage_crom_relocation_20261001/receipt.json.gz')

def build():
    original,ref=U.load(RECEIPT,True)
    comparisons=[]
    for banks in (6,9,16):
        old,oldref=U.load((OLD,PREFIX+f'stage_local{banks}.json'))
        new,newref=U.load((NEW,PREFIX+f'stage_local{banks}_SS17.json'))
        if old['rank_values']!=new['rank_values'] or old['regular_element']!=new['regular_element']:
            raise ValueError('physical value/validity mapping or geometry changed')
        if new['SS_route_basis']['stages_each_direction']!=17 or new['SS_route_basis']['historical11_qualified'] is not False:
            raise ValueError('corrected route scope mismatch')
        ticks={2:0,4:0,128:0}; pcs=set()
        for a,b in zip(old['stages'],new['stages'],strict=True):
            if {k:v for k,v in a.items() if k!='commands'}!={k:v for k,v in b.items() if k!='commands'}:
                raise ValueError('stage mapping/catalog identity changed')
            for ca,cb in zip(a['commands'],b['commands'],strict=True):
                if {k:v for k,v in ca.items() if k!='finite_services'}!={k:v for k,v in cb.items() if k!='finite_services'}:
                    raise ValueError('command coverage/address route changed')
                pcs.add(cb['PC'])
                for sa,sb in zip(ca['finite_services'],cb['finite_services'],strict=True):
                    if sb['credits']!=sa['credits'] or sb['actual_absolute_PC_release'] is not None:
                        raise ValueError('actual release or credit contract changed')
                    if sb['finite_fill_and_reverse_credit_ticks']<sa['finite_fill_and_reverse_credit_ticks']:
                        raise ValueError('unpriced faster corrected service')
                    ticks[sb['credits']]+=sb['finite_fill_and_reverse_credit_ticks']
        if len(pcs)!=491: raise ValueError('complete command coverage')
        comparisons.append(dict(banks=banks,historical_model=oldref,current_service_model=newref,
            value_validity_catalog_and_geometry_byte_fields_identical=True,
            SS_route_basis=new['SS_route_basis'],
            conditional_coefficient_only_us_per_reference_rank={str(k):str(Decimal(v)/3600) for k,v in ticks.items()},
            actual_absolute_PC_release=None,actual_service_bound=False))
    return dict(schema='w11.stage-CROM-SS17-binding.v1',original_compiler_receipt=ref,
        historical_diagnostic_programs=[dict(rank=r['rank'],diagnostic_program_sha256=r['diagnostic_program_sha256'],
            published_program_sha256=None,runnable=False) for r in original['ranks']],
        current_models=comparisons,
        historical_11_cycle_evidence_preserved=True,historical_11_cycle_timing_credit=False,
        compiler_address_and_value_proof_unchanged=True,
        inherited_numeric_or_runtime_pass=False,
        L1_invalid_local_slots=[12528,33008],L1_source_authority=None,
        actual_wide_bus_capacity_and_reach_bound=False,actual_service_bound=False,
        actual_physical_home=None,actual_contextual_SS_FF=False,
        image_admission=False,hardware_admission=False,full_token_latency=None,
        checkpoint_payload_reads=0,jobs_launched=0)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);args=p.parse_args()
    path=Path(args.output)
    if path.exists(): raise ValueError('preserve previous evidence')
    path.write_text(json.dumps(build(),indent=2,sort_keys=True)+'\n')
