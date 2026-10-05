import importlib.util
import json
from pathlib import Path

import pytest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('parallel',ROOT/'tools/dsrom_parallel_owner_capacity_calendar.py')
M=importlib.util.module_from_spec(spec);spec.loader.exec_module(M)


@pytest.fixture(scope='module')
def model():return M.build()


def test_all_actual_matrices_and_Engram_grain(model):
    assert model['full46509_metadata_run_census_bound']
    assert model['single_die_overcapacity_operator_count']==2
    assert model['max_active_pairs_by_shard']==[1600,1600]
    for r in model['largest_unpartitionable_Engram_witness']:
        assert r['active_unique_pairs']==[1600,1600]
        assert not r['single2048_die_complete_operator_fit']
        assert r['source_root_regions_cut']==0 and r['K']==6144
    assert [(r['stage'],r['phase']) for r in model['largest_unpartitionable_Engram_witness']]==[(1,298),(18,579)]


def run():
    return dict(compiled_NP=4096,plans=[[0,0,0,1,128,8000,192]],layer=0,expert=None,alias='x',format='fp8',stage=0,rows=2,K=6144,segments=[[0,6144]],issue_cycles_LAT8_condition=192,ECC={},immutable_provider_home=0)


def test_logical8192_bank_is_two4096_leaves_not_depth_change():
    r=M.run_census(run());assert r['active_unique_pairs']==[1,0]
    d=run();d['plans'][0][-2]=8192
    with pytest.raises(ValueError):M.run_census(d)


def test_root_reassociation_rejected():
    d=run();d['plans'][0][1]=2048
    with pytest.raises(ValueError):M.run_census(d)


def test_padding_macro_cfg_return_debits_preserved(model):
    c=model['compiled_capacity']
    assert c['local_NP']==2048 and c['local_BF_dual_sites']==362
    assert c['all721_original_padding_retained']
    assert c['cfg4096x72_macros_per_shard']==14336
    assert c['all58x4x2_cfg_macros']==6651904
    assert c['cfg_physical_bits_per_shard']==4227858432
    assert c['return_declared_bits_per_shard']==34885504
    assert c['total_priced_per_shard_mm2']==pytest.approx(694.8828979212858)


def test_sidecar_not_halved_or_local_for_free(model):
    e=model['mandatory_remote_ECC']
    assert e['source_sidecar_sites_per_stage']==103 and e['all_sites_on_shard']==0
    assert len(e['declared_bits_by_stage'])==58
    assert e['max_fp4_active_pairs_per_shard']==[128,128]
    assert e['worst_declared_remote_sidecar_bits_per_stream_cycle']==2048
    assert e['no_sidecar_storage_halving_or_free_local_replica']
    assert model['cfg_ECC']['source_decoder_provider_and_terminal_fence_unimplemented']


def test_expert_payload_is_not_invented_bandwidth(model):
    x=model['expert_envelope']
    assert x['XN_broadcast_bytes_per_rank']==20480
    assert x['TP4_gathered_activation_bytes']==9216
    assert x['result_bytes_per_expert_per_rank']==5120
    assert x['ordered_six_plus_shared_last_bytes_per_rank']==35840
    assert x['do_not_add_per_expert_final_gathers_without_source_collective']
    assert x['ready_buffer_bytes_and_link_replica_lanes_and_ports_not_inferred_from_payload']


def profiles():
    edges={'XN_broadcast':(0,1,10),'cfg_ECC_fence':(0,1,12),'native_compute':(12,12,20),'ordered_result_gather':(20,20,30)}
    p={name:dict(source_receipt='pinned'+name,resource_calendar='one-global-calendar',timebase='streaming_cycle',ready_edge=r,accepted_edge=a,visible_edge=v,peak_live_bytes=64,reserved_bytes=64) for name,(r,a,v) in edges.items()}
    p['native_compute']['weight_code_scale_ECC_terminal_receipts']=['actual matching word/code/scale/ECC terminal']
    return p


def test_only_actual_deadlines_can_prove_zero_loss():
    assert M.accepted_deadline_delta(30,profiles())==0
    assert M.accepted_deadline_delta(25,profiles())==5


def test_capacity_overflow_refuses_overlap():
    p=profiles();p['XN_broadcast']['peak_live_bytes']=65
    with pytest.raises(ValueError):M.accepted_deadline_delta(30,p)


def test_compute_before_visibility_refused():
    p=profiles();p['native_compute']['accepted_edge']=5;p['native_compute']['ready_edge']=5
    with pytest.raises(ValueError):M.accepted_deadline_delta(30,p)


def test_ideal_independent_rank_or_clock_overlap_refused():
    p=profiles();p['XN_broadcast']['resource_calendar']='other-rank-free-calendar'
    with pytest.raises(ValueError):M.accepted_deadline_delta(30,p)
    p=profiles();p['XN_broadcast']['timebase']='serial_cycle_without_CDC'
    with pytest.raises(ValueError):M.accepted_deadline_delta(30,p)


def test_missing_or_zero_service_refused():
    p=profiles();p.pop('cfg_ECC_fence')
    with pytest.raises(ValueError):M.accepted_deadline_delta(30,p)


def test_weight_ECC_cannot_be_free_inside_compute():
    p=profiles();p['native_compute'].pop('weight_code_scale_ECC_terminal_receipts')
    with pytest.raises(ValueError):M.accepted_deadline_delta(30,p)
    p=profiles();p['XN_broadcast']['visible_edge']=p['XN_broadcast']['accepted_edge']
    with pytest.raises(ValueError):M.accepted_deadline_delta(30,p)


def test_head_and_table_no_layer_fit_transfer(model):
    h=model['head_and_tables'];assert h['largest_global_tensor_pairs']==2525
    assert h['no_dedicated_head_phase_in_layer_map'] and h['head_ports_cfg_ECC_and_ordered_consumers_still_unbound']
    assert h['source_dedicated_provider_ledger']['head_storage_pairs_per_die_ceiling']==632
    assert h['source_dedicated_provider_ledger']['head_dies']==8


def test_Qr11_exact_protocol_compute_telescope(model):
    h=model['measured_HBM_Qwen_connected_schedule'];cases={r['case']:r for r in h['cases']}
    for i in (3,4):
        r=cases[i];assert sum(r['segments_cycles'].values())==19504
        assert r['dependent_SIMD_ops']==1024
        assert r['segments_cycles']['fence_to_first_SIMD_accept']==2
        assert r['segments_cycles']['first_SIMD_pass_including_directed_completion_holds']==9722
    assert cases[3]['last_visible_to_issue_cycles']==19508
    assert cases[4]['last_visible_to_issue_cycles']==19748
    assert h['testbench_policy']['SIMD_completion_held_cycles_each_vector']==4
    assert h['testbench_policy']['operand_read_response_held_cycles']==6
    assert not h['provider_natural_II_inferred'] and not h['pure_launch_cost_inferred']
    assert not h['SSFF_or_frequency_credit']


def test_no_selection_or_cacheless_free_compute(model):
    assert not model['partition_count_or_NP_selected'] and not model['build_admitted']
    assert model['DS_and_Qwen_workspaces']['existing_workspace_debits_retained_until_source_bound_replacement']
    assert model['accepted_calendar_contract']['actual_critical_path_delta_not_yet_bound']


def test_byte_replay(model):
    assert (M.OUT/'model-r5.json').read_text()==json.dumps(model,indent=2,sort_keys=True)+'\n'
