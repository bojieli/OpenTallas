from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import ds_mtp_accept_leaf_model as M

def prepared(g=5,a=5):
 l=M.Leaf(cold_fenced=True);r=l.step(start=(1048575,128799,g));assert r['accepted']==['start'];lease=l.lease
 targets=[100000+i for i in range(g+1)]
 drafts=targets[:g]
 if a<g:drafts[a]=120000
 for i in range(g+1):
  e={'amax':(lease,i,targets[i])}
  if i<g:e['tokx']=(lease,i+1,drafts[i])
  r=l.step(**e);assert not r['fault'];l.step()
 return l,lease,targets

def finish(l,lease,g=5):
 assert l.step(accept=(lease,g))['accepted']==['accept']
 r=l.step();assert not r['out_valid'];r=l.step();assert not r['out_valid'];r=l.step();assert r['out_valid'];return r

@pytest.mark.parametrize('g',range(8))
def test_all_prefix_lengths_class_A(g):
 for a in range(g+1):
  l,lease,ts=prepared(g,a);r=finish(l,lease,g)
  assert (r['result']['a'],r['result']['n'],r['result']['bonus'])==(a,a+1,ts[a])
  assert r['frame'][:a+1]==ts[:a+1]
  before=l.words.copy()
  for _ in range(4):assert l.step()['out_valid']
  assert l.view()['result']['done']==0
  assert l.step(consume=lease)['accepted']==['consume']
  assert l.view()['header']['phase']==M.DRAIN
  assert l.step(fence=(lease,63))['accepted']==['fence'];l.step()
  assert l.view()['header']['phase']==M.IDLE

@pytest.mark.parametrize('value',[0,1,0x0123456789abcdef,(1<<64)-1])
def test_source_codec_all_single_and_double_errors(value):
 c=M.encode64(value);assert M.decode64(c)==(value,False,False)
 for bit in range(72):assert M.decode64(c^(1<<bit))==(value,True,False)
 for a in range(72):
  for b in range(a+1,72):assert M.decode64(c^(1<<a)^(1<<b))[2]

@pytest.mark.parametrize('bad',[M.VOCAB,1<<21,-1])
def test_token_bounds(bad):
 l=M.Leaf(cold_fenced=True);assert l.step(start=(1,bad,5))['fault']

@pytest.mark.parametrize('which',['tokx','amax','accept'])
def test_wrong_source_lease(which):
 l=M.Leaf(cold_fenced=True);l.step(start=(10,128799,5));pos,gen=l.lease
 value=((pos,gen^1),1,100000) if which!='accept' else ((pos,gen^1),5)
 assert l.step(**{which:value})['fault'];assert l.view()['s0']['valid']

def test_missing_freshness_not_stale_old_slots():
 l=M.Leaf(cold_fenced=True);l.step(start=(10,100,5));lease=l.lease;l.step(accept=(lease,5));assert l.step()['fault']

@pytest.mark.parametrize('which,slot',[('tokx',0),('tokx',6),('amax',6),('amax',-1)])
def test_slot_bounds_and_pending_slot_zero(which,slot):
 l=M.Leaf(cold_fenced=True);l.step(start=(10,100,5));assert l.step(**{which:(l.lease,slot,100)})['fault']

def test_duplicate_slot_discovery_blocks_matching_consume():
 l,lease,_=prepared();l.step(tokx=(lease,1,100000));assert l.view()['fault']['bad']
 l,lease,_=prepared();finish(l,lease);state=l.words.copy()
 r=l.step(consume=(lease[0],lease[1]^1));assert r['fault'];assert l.words['result']==state['result']

def test_query_credit_held_and_stop_preserves_owned_debt():
 l=M.Leaf(cold_fenced=True);l.step(start=(1,100000,5));lease=l.lease
 r=l.step(amax=(lease,0,100001));assert r['accepted']==['amax']
 r=l.step(amax=(lease,1,100002),stop=True);assert 'amax' not in r['accepted'];assert l.view()['t0']['valid']
 with pytest.raises(ValueError):l.cold_reset(allcopies_fenced=True)
 assert l.step(rearm=63)['fault']

def test_single_error_corrected_before_prefix_and_double_error_no_release():
 l,lease,_=prepared();l.inject('t0',17);r=finish(l,lease);assert r['result']['bonus']!=0;assert l.view()['header']['corrected']
 l,lease,_=prepared();finish(l,lease);before=l.words['result'];l.inject('t0',0,1)
 r=l.step(consume=lease);assert r['fault'] and not r['accepted'];assert l.words['result']==before

def test_padding_valid_codeword_refused():
 l=M.Leaf(cold_fenced=True);l.words['header']=M.encode64(1<<63);assert l.step()['fault']

def test_positive_wrap_not_local_empty_or_run_cap():
 l=M.Leaf(cold_fenced=True)
 for i in range(40):
  l.step(start=(100+i,120000,0));lease=l.lease
  l.step(amax=(lease,0,120001));l.step();finish(l,lease,0)
  l.step(consume=lease);l.step(fence=(lease,63));l.step()
 assert l.view()['header']['gen']==8

@pytest.mark.parametrize('mask',[0,1,31,62])
def test_missing_positive_receipts_cannot_release(mask):
 l,lease,_=prepared(0,0);finish(l,lease,0);l.step(consume=lease)
 before=l.words.copy();assert l.step(fence=(lease,mask))['fault'];assert l.words['s0']==before['s0']

def test_reset_requires_external_fence():
 with pytest.raises(ValueError):M.Leaf()
 l=M.Leaf(cold_fenced=True)
 with pytest.raises(ValueError):l.cold_reset()

@pytest.mark.parametrize('name',M.FIELDS)
def test_each_mutable_record_has_positive_protection(name):
 l=M.Leaf(cold_fenced=True);l.inject(name,0,1);assert l.step()['fault']

def test_model_full_width_price_and_once_only_join():
 m=M.model();assert m['source_baseline_raw_FF']==366;assert m['raw_leaf_state_bits']==614
 assert m['protected_total_bits']==27*72 and m['service_boundary_signal_tracks_required']==636
 assert m['matched_baseline_debit']['actual_cell_overlap_and_net_area'] is None
 assert m['admission']['missing_whole_drafter_blocks_separate_leaf'] is False
 assert m['admission']['RTL_or_P_and_R_authorized_by_this_receipt'] is False

def test_source20_select_highbits_and_held_origin_not16_zeroextend():
 l=M.Leaf(cold_fenced=True);l.step(start=(1048575,128799,5));lease=l.lease
 c=M.CallerAdapter();c.capture_select(113689,lease)
 e=c.tokx(1);assert e['tokx'][2]==113689 and not e['caller_bad']
 assert l.step(**e)['accepted']==['tokx'];c.release_origin('tok_origin',matching_handshake=True)
 assert l.step()['fault'] is False;assert l.view()['s1']['token']==113689

@pytest.mark.parametrize('record',['select','tok_origin','amax_origin'])
def test_caller_protection_blocks_joint_consume_on_discovery(record):
 l,lease,_=prepared();finish(l,lease)
 c=M.CallerAdapter();c.capture_select(113689,lease);c.capture_origin('amax_origin',lease)
 c.words[record]^=3
 _,bad=c.inspect();assert bad
 before=l.words['result'];r=l.step(caller_bad=bad,consume=lease)
 assert r['fault'] and not r['accepted'];assert l.words['result']==before

def test_caller_single_error_and_no_unaccepted_origin_release():
 c=M.CallerAdapter();c.capture_select(103774,(1048575,1));c.words['select']^=1<<17
 e=c.tokx(1);assert not e['caller_bad'] and e['tokx'][2]==103774
 with pytest.raises(ValueError):c.release_origin('tok_origin',matching_handshake=False)
 with pytest.raises(ValueError):c.capture_origin('tok_origin',(1048576,2))
