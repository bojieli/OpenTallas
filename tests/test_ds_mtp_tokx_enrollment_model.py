import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import ds_mtp_tokx_enrollment_model as M
import ds_mtp_accept_leaf_model as L

def test_actual_static_fp32_draft_branch_not_bf16_xsel():
 r=M.source_branch();assert r['actual_branch'].startswith('S_SEL');assert r['actual_count_dynamic'] is False
 assert 'xu_d_n' not in r['draft_keywords']

@pytest.mark.parametrize('k',[1,16,512,2048])
def test_exact_source_scalar_width_register_delta(k):
 before=M.scalar_bits(k,16);after=M.scalar_bits(k,21)
 assert after[1]-before[1]==5*(3*k+2)
 assert sum(after[0].values())==after[1]

@pytest.mark.parametrize('kind,slot',[('tokx',1),('tokx',7),('amax',0),('amax',7)])
@pytest.mark.parametrize('token',[65536,103774,113689,129279])
def test_original_stamp_then_full21_token_stays_held(kind,slot,token):
 h=M.ProducerHolders();lease=(1048575,15)
 assert h.begin(kind,lease,slot)
 assert h.request(kind) is None
 assert h.finish(kind,lease,slot,token)
 snapshot=dict(h.words)
 assert not h.begin(kind,(1048576,0),slot)
 assert not h.finish(kind,lease,slot,token)
 assert not h.take(kind,(1048575,0),slot)
 assert h.words==snapshot
 assert h.request(kind)==(lease,slot,token)
 assert h.take(kind,lease,slot);assert h.request(kind) is None

@pytest.mark.parametrize('token',[-1,129280,1<<21])
def test_bounds_refuse_without_changing_accepted_debt(token):
 h=M.ProducerHolders();assert h.begin('tokx',(31,3),1);old=dict(h.words)
 assert not h.finish('tokx',(31,3),1,token);assert h.words==old

def test_slot_and_same_epoch_wrong_terminal_refused():
 h=M.ProducerHolders();assert h.begin('tokx',(31,3),2);old=dict(h.words)
 assert not h.finish('tokx',(31,3),3,113689);assert h.words==old
 assert not h.finish('tokx',(32,3),2,113689);assert h.words==old

@pytest.mark.parametrize('name',['tokx_value','tokx_origin','amax_value','amax_origin'])
def test_uncorrectable_holder_does_not_release(name):
 h=M.ProducerHolders();kind=name.split('_')[0];slot=1
 assert h.begin(kind,(21,7),slot);assert h.finish(kind,(21,7),slot,103774)
 h.words[name]^=3;old=dict(h.words)
 assert h.read(kind)['bad'];assert h.request(kind) is None
 assert not h.take(kind,(21,7),slot);assert h.words==old

def test_corrected_origin_and_token_are_used_before_accept():
 h=M.ProducerHolders();assert h.begin('tokx',(21,7),1);assert h.finish('tokx',(21,7),1,113689)
 h.words['tokx_value']^=1<<13;h.words['tokx_origin']^=1<<25
 assert h.request('tokx')==((21,7),1,113689)

def test_new_tuple_after_release_not_old_fresh_token():
 h=M.ProducerHolders();assert h.begin('tokx',(21,7),1);assert h.finish('tokx',(21,7),1,113689)
 assert h.take('tokx',(21,7),1);assert h.begin('tokx',(22,8),1)
 assert h.request('tokx') is None
 assert not h.finish('tokx',(21,7),1,113689)
 # Actual same-tuple reuse remains prohibited until external matched allcopies fence.

@pytest.mark.parametrize('kind,slot',[('tokx',0),('tokx',8),('amax',8)])
def test_destination_bounds(kind,slot):assert not M.ProducerHolders().begin(kind,(0,0),slot)

def test_additive_kernel_price_and_unknown_admission():
 m=M.model();c=m['kernel_composition']
 assert c['new_raw']==716 and c['new_protected']==2016 and c['raw_delta']==29
 assert c['cell_counts_total']['DFFASRHQNx1_ASAP7_75t_R']==2016
 assert m['source_holders']['raw_bits']==2*(22+29)
 assert m['physical_slot']['requested_height_um']==pytest.approx(191.7)
 assert not m['physical_slot']['fit_qualified']
 assert m['clock']['loaded_codec_selector_paths_or_closure_proven'] is False
 assert m['scalar_repair']['raw_FF_width_delta']==7690
 assert m['enrollment']['rate_claim'] is None
 assert m['default_enable'] is False

def test_source_holder_to_existing_leaf_exact_prefix_no_free_provider_release():
 h=M.ProducerHolders();leaf=L.Leaf(cold_fenced=True)
 leaf.step(start=(1048575,5,1));lease=leaf.lease
 assert h.begin('tokx',lease,1);assert h.finish('tokx',lease,1,113689)
 # reference leaf source requests are carried with original full lease and slot.
 rq=h.request('tokx');assert rq==(lease,1,113689)
 r=leaf.step(tokx=rq,amax=(lease,0,113689));assert 'tokx' in r['accepted']
 assert h.take('tokx',lease,1);leaf.step()
 assert h.begin('amax',lease,1);assert h.finish('amax',lease,1,103774)
 r=leaf.step(amax=h.request('amax'));assert 'amax' in r['accepted']
 assert h.take('amax',lease,1);leaf.step()
 assert leaf.step(accept=(lease,1))['accepted']==['accept']
 leaf.step();leaf.step();r=leaf.step()
 assert r['out_valid'] and r['result']['a']==1 and r['result']['bonus']==103774
 assert leaf.view()['header']['phase']==L.OUTPUT  # no provider/KV release inferred
