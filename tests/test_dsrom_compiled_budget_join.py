import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import dsrom_compiled_budget_join as J

def test_full_declaration_not_active_mask():
    x=J.config(4096,10)
    assert x['declared_bits_all_compiled_pairs']==5033164800
    assert J.config(3375,10)['declared_bits_all_compiled_pairs']==4147200000
    assert x['physical4096x274_macros']==6560

def test_word_mapping_unique_and_bounded():
    x=J.config(4096,10); locations=set()
    for pair in (0,4,5,4095):
        for index in range(x['words_per_pair']):
            loc=(pair//5,2*((index>>1)//4096)+(index&1),(index>>1)%4096,pair%5)
            assert loc not in locations
            locations.add(loc)
            assert loc[1]<8 and loc[2]<4096

def test_secded_layout_complete_without_free_spare():
    m=J.proposed_SECDED_mapping()
    assert len(m['payload_physical_bits'])==240
    assert len(m['Hamming_parity_physical_bits'])==8
    occupied=m['payload_physical_bits']+m['Hamming_parity_physical_bits']+[m['overall_parity_physical_bit']]
    assert len(set(occupied))==249 and set(occupied)==set(range(249))
    assert set(occupied).isdisjoint(m['unused_physical_bits'])

def test_frozen_attempt8_and_two_distinct_providers():
    x=J.build();cfg=x['configuration_provider'];a=x['exact_once_area_ledger_mm2']
    assert x['input_receipts'][0]['commit'].startswith('24d509c13')
    assert x['per_stage_config_requirements'][0]['phase_count']==874
    assert cfg['macro_body_mm2']==pytest.approx(51.701753088)
    assert a['config_prospective_body_plus_local_mux']==pytest.approx(69.19074349056)
    assert a['full_compiled_q_BF_catalog_frames']==pytest.approx(322.1036365536)
    assert a['declared_return_FF50_proxy']==pytest.approx(52.89758742528)
    assert a['conservative_no_containment_credit_die_total']>858
    assert not x['full_token_or_physical_admission']
    assert x['allocator_first_failure']['layer']==29

def test_exact_once_named_service_and_unknown_residual():
    a=J.build()['exact_once_area_ledger_mm2']
    terms=['full_compiled_q_BF_catalog_frames','declared_return_FF50_proxy','config_prospective_body_plus_local_mux','RNE_BF724_upper_proxy','WAKE_full_compiled_upper_proxy']
    assert sum(a[t] for t in terms)==pytest.approx(a['composed_priced_field_terms'])
    assert a['counterfactual_unknown_native_residual_disjoint_total']-a['composed_priced_field_terms']==pytest.approx(47.208013178655904)
    assert a['conservative_no_containment_credit_die_total']==pytest.approx(a['inherited_service_routes_clockPG_debit']+a['counterfactual_unknown_native_residual_disjoint_total'])

def test_loader_latency_not_claimed_or_phase_count_multiplied():
    x=J.build();l=x['configuration_provider']['source_loader_cycle_model']
    assert l['additional_cycles_per_actual_cfg_event']==2 and not l['cycle_credit_qualified']
    assert x['critical_path_latency']['no_actual_whole_token_cycles']
    assert x['configuration_provider']['baseline_overlap_credit']==0


def test_authoritative_closure_not_active_only_draft_stats():
    x=J.build();a=x['authoritative_closure']
    assert x['input_receipts'][0]['path'].endswith('closure_r2/closure.json')
    assert a['capacity_verdict']=='FAIL_CANDIDATE_PLACEMENT'
    assert len(a['unallocated_matrices'])==12202
    assert sum(a['declaration_counts_by_format'].values())==46509
    assert sum(a['placed_counts_by_format'].values())==34307
    assert a['actual_instruction_descriptors']==4778
    assert not a['all_descriptor_node_rank_provider_and_calendar_bindings_complete']
    assert x['source_ledger_validation']['physical4096_macros']==16384
    assert x['source_ledger_validation']['padding_pairs']==721
    assert x['per_stage_config_requirements'][0]['owner_compiled_cfg_bits']==5033164800
    assert x['configuration_provider']['source_loader_cycle_model']['source_declared_cfg_load_cycles_per_phase']==27
    assert not a['minimum_stage_claim']


def test_budget_replay_needs_no_historical_git_or_current_receipt_path(monkeypatch,tmp_path):
    import subprocess
    def refused(*args,**kwargs):raise AssertionError('historical git lookup forbidden')
    monkeypatch.setattr(subprocess,'check_output',refused)
    monkeypatch.setattr(J.B,'ROOT',tmp_path)
    x=J.build()
    assert x['exact_once_area_ledger_mm2']['conservative_no_containment_credit_die_total']==pytest.approx(924.2886185238459)
    assert x['input_receipts'][4]['sha256']=='f8a2f1333f31dcded2bf068ce4a21a9741f9cf2e88e58baba0b71386802a4223'

def test_changed_metadata_refused(monkeypatch,tmp_path):
    import shutil
    for f in J.METADATA_ROOT.iterdir():shutil.copyfile(f,tmp_path/f.name)
    monkeypatch.setattr(J,'METADATA_ROOT',tmp_path)
    manifest=__import__('json').loads((tmp_path/'manifest.json').read_text())
    (tmp_path/manifest['inputs'][0]['snapshot']).write_text('{}')
    with pytest.raises(ValueError,match='bytes changed'):J.build()

def test_changed_metadata_manifest_refused(monkeypatch,tmp_path):
    monkeypatch.setattr(J,'METADATA_ROOT',tmp_path)
    (tmp_path/'manifest.json').write_text('{}')
    with pytest.raises(ValueError,match='manifest currency'):J.build()
