import importlib.util
from pathlib import Path
import pytest
P=Path(__file__).resolve().parents[1]/'tools/dsrom_PAR2_minimal_context_admission.py'
S=importlib.util.spec_from_file_location('entry',P);M=importlib.util.module_from_spec(S);S.loader.exec_module(M)
@pytest.fixture(scope='module')
def entry():return M.build()
def test_complete_existing_decoder_ports_and_replicas(entry):
    a,b=entry['decoder_entries'];assert (a['K'],a['N'],a['replicas_per_shard1_die'])==(256,266,412)
    assert (b['K'],b['N'],b['replicas_per_shard1_die'])==(272,282,256)
    assert a['output_bits']==258 and b['output_bits']==274
    assert a['syndrome_XOR2_nodes']==1040 and b['syndrome_XOR2_nodes']==1098
def test_characterize_without_parent_token_gate(entry):
    assert entry['existing_decoder_characterization_admitted']
    assert all(e['other_projects_are_not_characterization_gates'] for e in entry['decoder_entries'])
    assert not entry['fulltile_or_die_PR_admitted']
def test_no_zero_cost_or_clock_relaxation(entry):
    assert all(p>0 for p in entry['composed_latency']['per_dependency_path_cycles'].values())
    assert entry['target']['SS_setup_uncertainty_ps']==60 and entry['target']['FF_hold_uncertainty_ps']==25
    assert not entry['composed_latency']['no_token_loss_proven']
def test_header_and_every_stage_register_cost(entry):
    h=entry['capture_header_bit_contract'];assert sum(h[k] for k in ('stage','rank','shard','phase','opseq','era','provider_index','MB','parity','physical_row','corrected_uncorrectable','word_kind','valid'))==58
    bits=sum(e['replicas']*e['bits']*e['cycles'] for e in entry['capture_header_entries'])
    assert bits==entry['area']['prospective_fullwidth_reference_register_bits']
    assert entry['area']['no_containment_overlay_FF50_mm2']>0
def test_current_physical_area_not_old_body(entry):
    assert entry['area']['current_physical_construction_screen_mm2']==pytest.approx(732.9650770579258)
    assert entry['area']['conservative_screen_with_all_pipeline_overlay_mm2']>732.965
    assert entry['area']['new_macro_instances']==0 and not entry['area']['physical_fit_proven']
def test_endpoint_width_not_assumed_bandwidth(entry):
    e=entry['endpoint_entry'];assert e['peak_data_bits_per_stream_cycle']==2048
    assert e['representative_cut_bits']==528 and e['modeled_reply_pipeline_cycles']>1
    assert e['actual_per_call_endpoint_pins_lengths_tracks_and_link_resources_required_for_tile']

def test_headers_and_offered_words_are_not_free_transport(entry):
    e=entry['endpoint_entry'];assert e['full_reply_bits_per_stream_cycle']==9472
    assert e['representative_cut_with_proposed_headers_bits']==2442
    assert not e['routing_track_capacity_measured']
    c=entry['source_stream_join_contract'];assert c['config_source_last_capture_edge']==26 and c['config_source_safe_GO_edge']==27
    assert c['offered_indices_are_not_accepted_cycles']
    assert c['no_acceptance_or_prefetch_overlap_credit_from_static_offered_words']
