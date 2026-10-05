"""Join exact-once fragment inventory to fresh typed power, no E32 transfer."""
import argparse,hashlib,json,subprocess
from decimal import Decimal as D
from pathlib import Path

SOURCES={
 'consumed_once':('ca5a444d0','results/quality/w16_engram_rom_constructive_home_20261001/two_fragment_contract_consumed_once.json'),
 'typed_power':('7c0d2c556','results/uarch/w10_engram_fragment_power_r1/budget.json'),
 'identity_checker':('f69892ddd','results/quality/w16_w17_crom_finite_prefetch_20261001/fragment_credit_contract.json'),
}

def build():
    records={};pins={}
    for name,(commit,path) in SOURCES.items():
        data=subprocess.check_output(['git','show',commit+':'+path])
        records[name]=json.loads(data)
        pins[name]=dict(commit=commit,path=path,sha256=hashlib.sha256(data).hexdigest())
    c=records['consumed_once'];p=records['typed_power'];i=records['identity_checker']
    by_id={h['home_id']:h for h in c['homes']}
    assert len(by_id)==len(p['homes'])==192
    assert sum(h['total_storage_FF_bits'] for h in c['homes'])==p['aggregate_FF_bits']==3595629118
    assert sum(h['new_fragment_reassembly_and_control_FF_bits'] for h in c['homes'])==p['aggregate_new_FF_bits']==1522003968
    for h in p['homes']:
        expected=by_id[h['home_id']]
        assert h['actual_macros']==expected['actual_macros']
        assert h['priced_reservation']['FF_bits']==expected['total_storage_FF_bits']
        assert h['prior_FF_bits']==expected['preserved_prior_FF_bits']
        assert h['new_FF_bits']==expected['new_fragment_reassembly_and_control_FF_bits']
        assert D(h['clock_plus_leak_W'])+D(h['margin_before_data_hub_PHY_W'])==D('474.56')
    largest=max(p['homes'],key=lambda h:D(h['clock_plus_leak_W']))
    return dict(schema='opentallas.w17.DSROM-fragment-power-join.v1',source_pins=pins,
        state=dict(homes=192,physical_macros=p['actual_macros'],all_ungated_FF_bits=p['aggregate_FF_bits'],
            additional_fragment_FF_bits=p['aggregate_new_FF_bits'],
            endpoint_count_per_home=c['response_hop_endpoint_count_per_home'],
            additional_FF_bits_per_endpoint=c['new_state_per_response_hop_bits'],
            consumed_once_state_encoding=c['new_state_recipe']),
        conditional_power=dict(maximum_home_clock_leak_W=largest['clock_plus_leak_W'],
            margin_before_serialized_data_PHY_hub_W=largest['margin_before_data_hub_PHY_W'],
            maximum_home_all_arcs_clock_leak_data_pin_allocation_W=largest['priced_reservation']['clock_leak_data_pin_subtotal_W'],
            all_arcs_is_not_physical_minimum=True,
            all192_ungated_clock_W=p['all192_ungated_clock_W'],
            serialized_selected_data_bound=False,complete_CTS_PHY_hub_RC_IR_bound=False),
        conditional_service=dict(response_fragments_per_lookup_per_hop=16,
            maximum_local_row_cycles=c['timing']['max_local_row_cycles'],
            no_old104_106cycle_credit=True,full_program_critical_path_bound=False),
        identity_admission=dict(required_model_epoch_bits=i['model_identity_bits']['epoch'],
            physical_fragment_recipe=c['packet']['tag_recipe'],candidate_epoch_bits=8,
            verdict='REJECT_EPOCH8_ACK_PROVIDER_NOT_BOUND',
            fresh_typed_epoch8_power_applies_to_epoch32_candidate=False,
            stored_ACK_identity_epoch32_setup_reset_drained_reuse_bound=False),
        boundary=dict(proposed_tracks=c['packet']['total_cut_tracks'],available_tracks=321,
            proposed_margin=11,fullwidth341track_failure_preserved=True,
            width_only_does_not_qualify_routing_or_service=True),
        next_correction='Bind full generation and stored-ACK identity transport, price every added endpoint/setup bit and serialized data event; then compose actual external lease and consumer path.',
        physical_admission=False,full_token_latency=None,headline_rate=None,
        checkpoint_reads=0,jobs_launched=0)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args()
    Path(a.out).write_text(json.dumps(build(),sort_keys=True,indent=2)+'\n')
