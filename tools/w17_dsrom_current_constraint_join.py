"""Join current local coefficient and Engram candidate constraints, fail closed."""
import argparse,hashlib,json,subprocess
from decimal import Decimal as D
from pathlib import Path

SOURCES={
 'local_CROM':('47b715428','results/quality/w16_w17_crom_finite_prefetch_20261001/local_home.json'),
 'Engram192':('65eb60a9d','results/quality/w16_engram_rom_constructive_home_20261001/sensitivity_192_homes.json'),
 'Engram192_power':('200e52bdf','results/uarch/w10_engram192_power_r1/budget.json'),
 'Engram192_obstacles':('35c3d7e319','results/quality/w16_engram_rom_constructive_home_20261001/sensitivity_192_obstacle_screen.json'),
}

def build():
    records={};pins={}
    for name,(commit,path) in SOURCES.items():
        data=subprocess.check_output(['git','show',commit+':'+path])
        records[name]=json.loads(data)
        pins[name]=dict(commit=commit,path=path,sha256=hashlib.sha256(data).hexdigest())
    p=records['Engram192_power'];g=records['Engram192'];c=records['local_CROM']
    assert p['all_storage_FF_bits']==g['all_storage_FF_bits']==2073429886
    assert p['actual_macros']==sum(h['actual_macros'] for h in g['homes'])==1500067
    assert len(p['homes'])==len(g['homes'])==192
    by_id={h['home_id']:h for h in g['homes']}
    for h in p['homes']:
        assert h['macros']==by_id[h['home_id']]['actual_macros']
        assert h['priced_reservation']['FF_bits']==by_id[h['home_id']]['total_storage_FF_bits']
        assert D(h['clock_plus_leak_W'])+D(h['margin_before_data_PHY_hub_W'])==D('474.56')
    largest=max(p['homes'],key=lambda h:D(h['clock_plus_leak_W']))
    arc=D(largest['priced_reservation']['clock_leak_data_pin_subtotal_W'])
    selected=next(r for r in c['scenarios'] if r['credits']==128)
    return dict(schema='opentallas.w17.DSROM-current-constraint-join.v1',source_pins=pins,
        candidate_decisions=dict(Engram_home_role='192 dedicated table-service dies, current die outline and retained hub',
            historical_replacement_groups=['ROM_MAC.expert','ROM_MAC.dense_QE','ROM_MAC.ME','ENGRAM.spill','ROM_MAC_strip'],
            mandatory_retained=['VM.CONSTANT_HE','hub','SRAM','HBM','PHY','IO','channels'],
            role_replacement_and_channel_void_placement_proof_pending=True,
            CROM=c['selected_model_candidate']),
        Engram=dict(homes=192,table_copies=1,physical_macros=1500067,all_ungated_FF_bits=2073429886,
            maximum_home_clock_and_leak_W=largest['clock_plus_leak_W'],
            margin_before_data_PHY_hub_W=largest['margin_before_data_PHY_hub_W'],
            all_arcs_clock_leak_data_pin_allocation_W=str(arc),
            all_arcs_allocation_excess_W=str(arc-D('474.56')),
            allocation_is_not_physical_minimum=True,
            all_home_ungated_clock_W=p['all192_component_totals_W']['ungated_clock_W'],
            full_retained_obstacle_placement='FAIL; source receipt preserved',
            selected_path_data_transition_enable_mask_and_macro_activity_proof_pending=True),
        CROM=dict(cold_delivery_partial_us=selected['cold_delivery_partial_us'],
            gamma_partial_us=selected['gamma_partial_us'],credits=128,
            per_direction_route_fast_cycles=c['registered_route_fast_cycles_each_direction'],
            retained_allocation_mm2=selected['retained_characterized_allocation_plus45macro_mm2'],
            placement_verdict=c['placement_verdict'],
            physical_coefficient_repack_tags_CDC_ports_SSFF_pending=True),
        operator_and_visibility_requirements=['Complete nonexpert, head, embedding and HC homes/ports',
            'Q/BF active phase data, clock, hub and mandatory reserves',
            'C/P/W/B old jobs, actual CKV stored-row peer ACK and epoch drain',
            'CWL+burst+backend visibility for nine writes; final attention consumer and reverse lease retirement',
            'Actual compute, norm/SFU, collectives, dispatch, refill and wake dependency calendar'],
        delivery_partials_composed_into_full_token_latency=False,
        latency_composition_rule='Do not sum delivery partials into full token until actual programme branches, resource sharing and consumers are bound. No overlap or historical headline credit.',
        no_idle_clock_credit=True,no_hub_removal_credit=True,
        next_minimum_correction='Channel-aware role-specific Engram placement and source-selected-path data activity; explicit CROM/SU displacement reservation and finite providers.',
        full_token_latency=None,headline_rate=None,physical_admission=False,
        checkpoint_reads=0,jobs_launched=0)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args()
    Path(a.out).write_text(json.dumps(build(),sort_keys=True,indent=2)+'\n')
