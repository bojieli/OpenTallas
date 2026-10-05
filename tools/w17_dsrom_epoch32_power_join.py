"""Current E32 state and retained-hub reservation; complete admission stays closed."""
import argparse,hashlib,json,subprocess
from decimal import Decimal as D
from pathlib import Path

SOURCES={
 'E32_contract':('9ef36f654','results/quality/w16_engram_rom_constructive_home_20261001/epoch32_fragment_contract.json'),
 'E32_power':('e3a1a53db','results/uarch/w10_engram_epoch32_power_r1/budget.json'),
 'retained_hub':('fea811df4','results/uarch/w10_q_existing_icg_r1/phases.json'),
}

def build():
    records={};pins={}
    for name,(commit,path) in SOURCES.items():
        raw=subprocess.check_output(['git','show',commit+':'+path])
        records[name]=json.loads(raw)
        pins[name]=dict(commit=commit,path=path,sha256=hashlib.sha256(raw).hexdigest())
    c=records['E32_contract'];p=records['E32_power'];hub=records['retained_hub']['hub']
    by_id={h['home_id']:h for h in c['state_inventory']['homes']}
    assert len(by_id)==len(p['homes'])==192
    assert sum(h['total_storage_FF_bits'] for h in by_id.values())==p['aggregate_FF_bits']==4361491198
    for h in p['homes']:
        assert h['priced_reservation']['FF_bits']==by_id[h['home_id']]['total_storage_FF_bits']
        assert h['source_state']==by_id[h['home_id']]
        assert D(h['clock_plus_leak_W'])+D(h['margin_before_data_control_hub_PHY_W'])==D('474.56')
    largest=max(p['homes'],key=lambda h:D(h['clock_plus_leak_W']))
    static=D(hub['total_static_reservation_W'])
    dynamic=sum(map(D,hub['configured_all_units_dynamic_upper_W'].values()))
    subtotal=D(largest['clock_plus_leak_W'])+static+dynamic
    return dict(schema='opentallas.w17.DSROM-E32-retained-hub-power-join.v1',source_pins=pins,
        inventory=dict(homes=192,macros=p['actual_macros'],ungated_FF_bits=p['aggregate_FF_bits'],
            old_FF_retained=p['all_old_FF_retained'],
            request_setup_beats=3,response_fragments_per_word=2,
            request_state_bits_per_hop=112,response_state_bits_per_hop=366,
            home_image_session_bits=293,home_root_rowlease_bits=92),
        power_allocation=dict(maximum_home_E32_clock_leak_W=largest['clock_plus_leak_W'],
            retained_hub_static_W=str(static),retained_hub_all_unit_dynamic_upper_W=str(dynamic),
            conditional_subtotal_W=str(subtotal),remaining_before_new_costs_W=str(D('474.56')-subtotal),
            included_hub_interface_idle_W=hub['interface_idle_W'],
            PHY_delta_rule='Reconcile new PHY/IO against included44.296W interface reservation; no duplicate charge or automatic fit/qualification.',
            all_home_clock_W=p['all192_ungated_clock_W'],
            allocation_is_not_physical_minimum=True,
            current_serialized_data_and_added_control_logic_bound=False,
            contextual_clock_tree_RC_IR_SSFF_qualified=False),
        preserved_generation_failure=c['legacy_E8_alias_witness'],
        finite_ACK_rule=c['storedACK'],
        scope='FreshE32 FF/clock/leak and retained historical hub allocation only. Comparator/serializer/control and image/setup/drain/provider calendar remain mandatory.',
        old2360cycle_E8_calendar_applies=False,
        full_program_critical_path=None,physical_admission=False,headline_rate=None,
        checkpoint_reads=0,jobs_launched=0)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args()
    Path(a.out).write_text(json.dumps(build(),sort_keys=True,indent=2)+'\n')
