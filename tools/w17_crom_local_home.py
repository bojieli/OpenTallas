"""Current SU-region local coefficient candidate; rejects unreserved SU fit."""
import argparse, hashlib, json, math, re, subprocess
from decimal import Decimal as D
from pathlib import Path
import w17_crom_finite_prefetch as C

def source(commit,path):
    data=subprocess.check_output(['git','show',commit+':'+path])
    return data,dict(commit=commit,path=path,sha256=hashlib.sha256(data).hexdigest())

def build():
    raw,fp_pin=source('541a1d2f','results/floorplan/v41_pack_refit_w10_interim.json')
    fp=json.loads(raw)
    region=next(r for r in fp['soft_regions'] if r[0]=='HUB_SU_VECTOR')
    raw,u_pin=source('541a1d2f','tools/uarch_model.py')
    text=raw.decode()
    values={name:D(re.search(r'^'+name+r'\s*=\s*([0-9.]+)',text,re.M)[1])
            for name in ('WIRE_PS_PER_UM_LOADED','WIRE_OVERHEAD_PS','UNCERTAINTY_PS')}
    distance=D(str(region[4]))+D(str(region[5]))
    segment=(D(2500)/3-values['WIRE_OVERHEAD_PS']-values['UNCERTAINTY_PS'])/values['WIRE_PS_PER_UM_LOADED']
    route=math.ceil(distance/segment)
    calendar=C.build(route=route)
    raw,power_pin=source('ebef36895','results/uarch/w10_crom_control_reservation_r1/budget.json')
    power=json.loads(raw)
    rows=[]
    for scenario in power['credit_scenarios']:
        credit=scenario['credits']
        # Preserve old characterized area as an allocation: do not subtract
        # historical route FF or clock without a new characterized ledger.
        area=D(scenario['conditional_combined_area_mm2'])+D('.354661416')
        rows.append(dict(credits=credit,cold_delivery_partial_us=calendar['candidate_delivery_partial_us_by_credit'][str(credit)],
            gamma_partial_us=calendar['gamma_partial_us_by_credit'][str(credit)],
            retained_characterized_allocation_plus45macro_mm2=str(area),
            old75route_power_not_subtracted=True,
            added_forward_control_pipeline_bits=route*64,
            added_reverse_control_pipeline_bits=(route+1)*64,
            ungated_added_control_clock_and_data_reservation_bound=False))
    return dict(schema='opentallas.w17.CROM-local-SU-candidate.v1',
        source_pins=dict(floorplan=fp_pin,wire_model=u_pin,historical_control_power=power_pin,
            encoded_calendar=calendar['source_pins']),
        selected_model_candidate=dict(layer_local_partial_homes=164,banks_per_home=45,
            total_banks=7380,credits=128,reason='Lowest enumerated finite cold-delivery partial; conditional choice, not adoption.'),
        SU_region_um=region[2:],local_manhattan_envelope_um=str(distance),
        registered_route_fast_cycles_each_direction=route,wire_segment_um=str(segment),
        scenarios=rows,software_control_catalog_exact=calendar['compiled_software_catalog'],
        logical_coefficient_reads_per_rank=549760,layer_cold_gamma_homes_per_rank=81,
        no_prefetch_overlap=True,no_idle_clock_credit=True,
        placement_verdict='REJECT_UNRESERVED_SU_DISPLACEMENT',
        mandatory_geometry_correction='Reserve coefficient macros, catalog, staging, CTS and two-direction routes explicitly; resize or relocate existing SU rather than reuse its full region twice.',
        actual_macro_and_SU_cell_coordinates_bound=False,
        current_SU_region_area_mm2=str(D(str(region[4]))*D(str(region[5]))/D(1000000)),
        full_operator_latency=None,physical_admission=False,headline_rate=None,
        scope='Current floorplan region-bound candidate distance; no actual placed route, source coefficient repack, CDC provider or contextual timing qualification.',
        checkpoint_reads=0,jobs_launched=0)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args()
    Path(a.out).write_text(json.dumps(build(),sort_keys=True,indent=2)+'\n')
