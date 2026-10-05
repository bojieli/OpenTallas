import json,sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import dsrom_I66_PAR2_calendar_join as J

@pytest.fixture(scope='module')
def inputs():
    return J.S.events('r2_PASS'),J.S.load(J.OUT/'inputs/I66_node_binding.json'),J.S.load(J.OUT/'inputs/I66_phase_ownership.json')

def test_all_observed_rows_follow_superrow_macro_and_original_tree_ownership(inputs):
    m=J.build(*inputs)
    assert m['per_source_shard']['0']['root_row_accept']==320
    assert m['per_source_shard']['1']['root_row_accept']==256
    assert sum(x['main_CE_accept'] for x in m['per_source_shard'].values())==23040
    assert all(x['cfg_element_write_accept']==51200 for x in m['per_source_shard'].values())
    assert m['ordered_K_grain']['paired_leaf_to_root_shard_crossings']==0
    assert m['boundary_widths']['cfg_word_bits']==48
    assert not m['physical_admission'] and not m['no_loss_proof']

@pytest.mark.parametrize('bad',['phase','root_owner','visibility_edge'])
def test_owner_and_terminal_mutants_rejected(inputs,bad):
    events,node,phase=inputs;ev=list(events)
    kind={'phase':'op_accept','root_owner':'root_row_accept','visibility_edge':'final_destination_visible'}[bad]
    idx=next(i for i,x in enumerate(ev) if x['kind']==kind);ev[idx]=dict(ev[idx])
    if bad=='phase':ev[idx]['phase']=13
    elif bad=='root_owner':ev[idx]['a']=(ev[idx]['a']+64)%128
    else:ev[idx]['edge']-=1
    with pytest.raises((ValueError,AssertionError)):J.build(ev,node,phase)

def test_conditional_fullprogram_origin_is_not_a_physical_zero_cost(inputs):
    m=J.build(*inputs);p=J.insert_at(m,1010)
    assert p['conditional_native_edges']==dict(last_root=1419,last_VM_visibility=1420,spine_idle=1421,adapter_idle=1422)
    assert p['physical_cfg_activation_root_added_edges'] is None and p['coll_busy_release'] is None
    assert not p['fullscheduler_or_provider_admission']

def test_exact_generator_replay_from_added_inputs(tmp_path):
    p=tmp_path/'model.json';J.generate(p)
    assert p.read_bytes()==(J.OUT/'model.json').read_bytes()
