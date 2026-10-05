"""Current repack/event intake; preserve historical power and route failures."""
import argparse,hashlib,json,subprocess
from pathlib import Path

SOURCES={
 'prior_join':('945aa520e','results/quality/w16_w17_crom_finite_prefetch_20261001/whole_constraint_join.json'),
 'role_repack':('2b98ba187','results/quality/w16_engram_rom_constructive_home_20261001/sensitivity_192_role_repack_constants_retained.json'),
 'event_contract':('c8ea5395d','results/quality/w16_engram_rom_constructive_home_20261001/repacked_192_enable_mask_contract.json'),
}

def build():
    records={};pins={}
    for name,(commit,path) in SOURCES.items():
        raw=subprocess.check_output(['git','show',commit+':'+path])
        records[name]=json.loads(raw)
        pins[name]=dict(commit=commit,path=path,sha256=hashlib.sha256(raw).hexdigest())
    prior=records['prior_join'];geo=records['role_repack'];events=records['event_contract']
    assert geo['legal_source_obstacle_rectangle_screen_pass']
    assert not geo['all8192_reserved_cell_retained_obstacle_pair_conflicts']
    assert geo['all_retained_channel_count']==16 and geo['all_retained_hard_count']==249
    assert sum(h['actual_macros'] for h in events['homes'])==1500067
    ff=sum(h['total_storage_FF_bits'] for h in events['homes'])
    assert ff==events['aggregate_repacked_storage_FF_bits']==2073625150
    assert not events['physical_data_provider_proven']
    assert not geo['physical_admission'] and not events['physical_admission']
    return dict(schema='opentallas.w17.DSROM-repacked-constraint-join.v1',source_pins=pins,
        geometry=dict(retained_cell_rectangle_screen='PASS_SCOPE_ONLY',
            retained_channels=16,retained_hard_instances=249,
            replacement_manifest_source=pins['role_repack'],
            origins_SHA256=geo['coordinate_construction']['all1500067_actual_macro_origin_tuple_SHA256'],
            CTS_PHY_selector_control_area_placement=geo['CTS_PHY_selector_control_area_placement']),
        current_event_inventory=dict(homes=192,macros=1500067,ungated_FF_bits=ff,
            selected_wire_path_cycles_range=[35,36],conditional_row_cycles_range=[104,106],
            selected_data_transition_contract=events['finite_runtime_transition_bounds_per_lookup'],
            actual_tree_data_isolation=False),
        power_currency=dict(historical_200e_inventory_FF_bits=prior['Engram']['all_ungated_FF_bits'],
            new_FF_bits_above_historical_200e=ff-prior['Engram']['all_ungated_FF_bits'],
            old_200e_power_applies_to_current_repack=False,
            historical_200e_power_summary=prior['Engram'],
            no_power_replication_or_halving_credit=True),
        preserved_fullwidth_route_failure=dict(required_tracks=341,available_tracks=321,shortfall=20,
            original_source_screen=geo['route_screen']),
        serialized_candidate_requirements=dict(response_data_bits=256,response_fragments_per_word=2,
            request_bits=51,ready_control_tracks=2,separate_stored_word_ACK_tracks=1,
            total_proposed_tracks=310,track_margin=11,
            ACK_rule='Fragment READY and second-fragment capture do not release consumer credit. Require matching complete-word storage and consumer acceptance, then stored-word ACK and reverse return.',
            additional_reassembly_state_at_all_physical_endpoints_not_selected_path_only=True,
            epoch_tag_no_wrap_reset_stale_duplicate_and_partial_fragment_gates_required=True,
            compiled_fragment_exactness_and_finite_calendar_bound=False,
            new_ungated_endpoint_state_power_bound=False),
        next_correction='Join constant-retained repack with all endpoint reassembly state, two-fragment service, full-word stored ACK, actual enable isolation and current ungated power before admission.',
        no_overlap_credit=True,no_idle_clock_credit=True,
        full_token_latency=None,headline_rate=None,physical_admission=False,
        checkpoint_reads=0,jobs_launched=0)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args()
    Path(a.out).write_text(json.dumps(build(),sort_keys=True,indent=2)+'\n')
