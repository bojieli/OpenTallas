import json,sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import ds_mtp_protected_scalar_origin_model as M

def native():
 n=M.NativeOrigins();assert n.accept(0,(8191,15),7,native_ready=True,holder_begin_ready=True);return n

def test_full_source_inventory_and_no_admission():
 m=M.model();assert m['state']['protected_bits']==112608
 assert m['state']['raw_bits']==69636
 assert m['state']['codewords']==1564
 assert m['calendar']['source_after_last_edges']==1026
 assert not m['admission']['RTL_authorized_by_this_model']
 assert m['ports']['score_stream_signals']==66
 assert m['cost']['reset7pin_fF']<=5.76
 assert m['cost']['net_area'] is None

@pytest.mark.parametrize('kind,slot',[(0,1),(0,7),(1,0),(1,7)])
def test_original_origin_and_held_matching_terminal(kind,slot):
 n=M.NativeOrigins();lease=(8191,15)
 assert n.accept(kind,lease,slot,native_ready=True,holder_begin_ready=True)
 assert n.observe(kind,idle=True,token=129279) is None
 assert n.observe(kind,idle=False,intermediate_ov=True,token=123) is None
 assert n.observe(kind,idle=False,intermediate_ov=True,token=100000) is None
 expected=(lease,slot,129279)
 assert n.observe(kind,idle=True,token=129279)==expected
 for _ in range(12):
  assert n.output(kind)==expected
  assert not n.take(kind,expected,ready=False)
  assert not n.accept(kind,lease,slot,native_ready=True,holder_begin_ready=True)
 assert n.take(kind,expected,ready=True)
 assert n.output(kind) is None
 # Empty origin is not authority to reuse same tuple in this cohort.
 assert not n.accept(kind,lease,slot,native_ready=True,holder_begin_ready=True)
 assert n.fault

@pytest.mark.parametrize('native_ready,holder_ready',[(False,True),(True,False),(False,False)])
def test_joint_acceptance_reserves_before_native_go(native_ready,holder_ready):
 n=M.NativeOrigins();assert not n.accept(0,(1,1),1,native_ready=native_ready,holder_begin_ready=holder_ready)
 assert n.cohort is None and not n.used

@pytest.mark.parametrize('bit',range(72))
def test_each_single_origin_fault_preserves_original_identity(bit):
 n=native();n.words[0]^=1<<bit
 assert n.read(0)['lease']==(8191,15) and n.read(0)['slot']==7
 assert n.observe(0,idle=False) is None
 assert n.observe(0,idle=True,token=70000)==((8191,15),7,70000)

@pytest.mark.parametrize('bit',range(72))
def test_each_single_cohort_fault_keeps_original_cohort(bit):
 n=native();n.cohort_word^=1<<bit
 assert n.cohort==(8191,15) and n.used=={(0,7)}
 assert not n.fault

@pytest.mark.parametrize('word',[0,1])
def test_double_origin_fault_quarantines(word):
 n=native();n.words[word]^=3
 with pytest.raises(ValueError):n.read(word)
 assert n.fault and n.output(0) is None

def test_cohort_double_fault_does_not_grant():
 n=native();n.cohort_word^=3
 with pytest.raises(ValueError):n.accept(1,(8191,15),0,native_ready=True,holder_begin_ready=True)

def test_source_reset_preserves_accepted_debt():
 n=native();old=n.words[:]
 assert n.observe(0,idle=True,source_reset=True) is None
 assert n.fault and n.words==old
 with pytest.raises(ValueError):n.fence((8191,15),allcopies=True,holders_empty=True,providers_idle=True)

def test_wrong_echo_discovery_blocks_retirement():
 n=native();n.observe(0,idle=False);out=n.observe(0,idle=True,token=100000);old=n.words[:]
 assert not n.take(0,((8191,0),7,100000),ready=True)
 assert n.fault and n.words==old

@pytest.mark.parametrize('missing', ['allcopies','holders_empty','providers_idle'])
def test_no_generation_wrap_from_local_empty(missing):
 n=native();n.observe(0,idle=False);out=n.observe(0,idle=True,token=70000);n.take(0,out,ready=True)
 args=dict(allcopies=True,holders_empty=True,providers_idle=True);args[missing]=False
 with pytest.raises(ValueError):n.fence((8191,15),**args)

def test_continuous_stream_wrap_requires_positive_fence_every_cohort():
 n=M.NativeOrigins()
 for i in range(40):
  lease=(8191+i,i%16)
  assert n.accept(0,lease,1,native_ready=True,holder_begin_ready=True)
  n.observe(0,idle=False);out=n.observe(0,idle=True,token=129279)
  assert n.take(0,out,ready=True)
  assert n.accept(1,lease,0,native_ready=True,holder_begin_ready=True)
  n.observe(1,idle=False);out=n.observe(1,idle=True,token=100000)
  assert n.take(1,out,ready=True)
  n.fence(lease,allcopies=True,holders_empty=True,providers_idle=True)

@pytest.mark.parametrize('k',[0,1,6,512])
def test_full_index_no_truncation_tie_signedzero_and_infinity(k):
 scores=[(129279,0x3f800000),(65535,0x3f800000),(65536,0x40000000),(0,0x80000000),(1,0),(2,0xff800000),(3,0x7f800000)]
 ranked=[3,65536,65535,129279,0,1,2]
 assert M.select(scores,k)==sorted(ranked[:k])

def test_nan_duplicate_bounds_refused():
 for scores in [[(0,0x7fc00000)],[(1,0),(1,0)],[(1<<21,0)]]:
  with pytest.raises(ValueError):M.select(scores,1)

def test_reserved_vm_returns_survive_output_stall():
 q=M.ReadReservations();assert q.issue(65536);assert q.issue(129279);assert not q.issue(4)
 q.capture(0x3f800000);q.capture(0x40000000)
 for _ in range(20):assert q.take(False) is None;assert not q.issue(4)
 assert q.take(True)==(65536,0x3f800000);assert q.issue(4)
 assert q.take(True)==(129279,0x40000000)
 q.capture(0);assert q.take(True)==(4,0)
 with pytest.raises(ValueError):q.capture(0)

def test_cold_model_is_byteexact():
 assert json.loads((M.OUT/'model.json').read_text())==M.model()

def test_no_index_without_valid_actual_amax():
 n=M.NativeOrigins();assert n.accept(1,(8191,1),0,native_ready=True,holder_begin_ready=True)
 n.observe(1,idle=False)
 assert n.observe(1,idle=True,token=0,result_valid=False) is None
 assert n.fault

def test_origin_position_overflow_refused_before_grant():
 n=M.NativeOrigins()
 assert not n.accept(0,(M.L.MASK,0),1,native_ready=True,holder_begin_ready=True)
 assert n.fault and n.words==[M.L.encode64(0)]*2

def test_source_bank_tail_is_not_first_output_only():
 m=M.model();assert m['calendar']['source_emit_post_first_tail_edges']==511
 assert m['calendar']['source_one_draft_segment_accepted_scores_plus_tail_edges']==129280+1026+511
 assert m['calendar']['whole_iteration_latency'] is None

def test_coded_semantic_origin_fault_and_stop_are_not_free_grants():
 n=native();raw=M.L.decode64(n.words[0])[0];n.words[0]=M.L.encode64(raw|(1<<53))
 with pytest.raises(ValueError):n.read(0)
 assert n.fault
 n=M.NativeOrigins();n.cohort_word=M.L.encode64(1<<41)
 assert not n.accept(0,(1,1),1,native_ready=True,holder_begin_ready=True)
