import sys,json,random,functools
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import ds_mtp_native_k1_model as M

@pytest.fixture(autouse=True,scope='module')
def memoize_pure_reference_codec():
 # Software-only bounded memoization of exact pure model codec values.
 # No architectural cache or changed source codec; restore after module tests.
 enc,dec=M.L.encode64,M.L.decode64
 M.L.encode64=functools.lru_cache(maxsize=4096)(enc)
 M.L.decode64=functools.lru_cache(maxsize=4096)(dec)
 yield
 M.L.encode64,M.L.decode64=enc,dec

def adapter(**kw):return M.NativeAdapter((8191,15),7,cold_fenced=True,**kw)
def launch(a,kind):
 assert a.offer(kind,slot=1 if kind==0 else 0,cmdpc=2213,engine=kind,amax=kind)
 assert a.arm(kind)
 begin=a.launch(kind,native_ready=True,holder_begin_ready=True);assert begin and begin[-1]==0
 assert a.launch_take(kind,lease=begin[0],cmdpc=2213,ready=True)
 return begin

def terminal(a,kind):
 begin=launch(a,kind)
 assert not a.observe(kind,idle=True,engine=kind,token=129279)
 for i in range(4):assert not a.observe(kind,idle=False,engine=kind,intermediate_ov=True,token=123)
 assert a.observe(kind,idle=True,engine=kind,token=129279)
 return begin

def test_source_pins_cost_and_separate_scope():
 m=M.model();n=m['native_adapter'];k=m['k1']
 assert n['cost']['codewords']==9 and n['cost']['protected_bits']==648
 assert k['cost']['codewords']==7 and k['cost']['protected_bits']==504
 assert m['comparison']['new_joint_gross50pct_mm2']<m['comparison']['reference_gross50pct_mm2']
 assert 'explicit_original_XU_K1_shared_VM_ports_mux_and_return_fanout' in k['cost']['cell_counts_by_section']
 assert n['source_ports']['own_fault_to_leaf_caller_bad_cut']==1
 assert k['source_K512_unchanged'] and not k['literal_RTL_gate_run']
 assert not m['comparison']['whole_token_saving_qualified']
 assert not m['admission']['physical_G0']

@pytest.mark.parametrize('kind',[0,1])
def test_actual_launch_and_matching_ctl_before_held_finish(kind):
 a=adapter();assert a.offer(kind,slot=int(kind==0),cmdpc=1737,engine=kind,amax=kind)
 assert a.output(kind) is None
 assert a.arm(kind)
 for _ in range(5):assert a.launch(kind,native_ready=False,holder_begin_ready=True) is None
 assert a.launch(kind,native_ready=True,holder_begin_ready=False) is None
 begin=a.launch(kind,native_ready=True,holder_begin_ready=True);lease=begin[0]
 # Unaccepted source receipt cannot be mistaken for consumed owner proof.
 assert not a.launch_take(kind,lease=lease,cmdpc=1737,ready=False)
 assert not a.observe(kind,idle=False,engine=kind,intermediate_ov=True)
 assert not a.observe(kind,idle=True,engine=kind,token=129279)
 assert a.launch_take(kind,lease=lease,cmdpc=1737,ready=True)
 assert a.observe(kind,idle=True,engine=kind,token=129279)
 assert a.output(kind) is None # actual CTL publication still missing
 assert a.ctl_offer(kind,lease=lease,slot=int(kind==0),lane=0,ctlpc=2213)
 assert a.ctl_check(kind)
 expected=(lease,int(kind==0),129279,1)
 for _ in range(20):
  assert a.output(kind)==expected
  assert not a.finish_take(kind,ready=False)
  assert not a.offer(kind,slot=2,cmdpc=999,engine=kind,amax=kind)
 assert a.finish_take(kind,ready=True)
 assert not a.ctl_take(kind,lease=lease,ctlpc=2213,ready=False)
 assert a.ctl_take(kind,lease=lease,ctlpc=2213,ready=True)
 assert a.output(kind) is None
 # Child history still prevents same tuple reuse without positive fence.
 assert not a.offer(kind,slot=int(kind==0),cmdpc=1737,engine=kind,amax=kind)
 with pytest.raises(ValueError):a.view()

@pytest.mark.parametrize('kind',[0,1])
def test_all_accepted_origin_single_bit_positions(kind):
 for word in range(3):
  for bit in range(72):
   a=adapter();begin=launch(a,kind);a.jobs[kind][word]^=1<<bit
   assert not a.observe(kind,idle=False,engine=kind)
   assert a.observe(kind,idle=True,engine=kind,token=70000)
   assert a.ctl_offer(kind,lease=begin[0],slot=begin[1],lane=0,ctlpc=2213)
   assert a.ctl_check(kind)
   assert a.output(kind)==(begin[0],begin[1],70000,1)

@pytest.mark.parametrize('record',['job0','job1','query0','query1','cohort'])
def test_current_double_fault_jointguard_blocks_all_launch(record):
 a=adapter();assert a.offer(0,slot=1,cmdpc=1737);a.arm(0);old=[x[:]for x in a.jobs]
 target={'job0':a.jobs[0],'job1':a.jobs[1],'query0':a.q[0],'query1':a.q[1],'cohort':a.c}[record]
 target[0]^=3
 with pytest.raises(ValueError):a.launch(0,native_ready=True,holder_begin_ready=True)
 # No backend acceptance phase update on discovered error.
 assert M.unpack(M.JOB,a.jobs[0])['phase']==M.ARM if record!='job0' else a.jobs[0][1:]==old[0][1:]

@pytest.mark.parametrize('kind',[0,1])
def test_source_reset_or_fault_does_not_erase_debt(kind):
 a=adapter();launch(a,kind);old=[x[:]for x in a.jobs]
 assert not a.observe(kind,idle=True,engine=kind,source_reset=True)
 assert a.jobs==old
 with pytest.raises(ValueError):a.view()

def test_discovery_edge_cannot_launch():
 a=adapter();assert a.offer(0,slot=1,cmdpc=1737);a.arm(0);old=[x[:]for x in a.jobs]
 assert a.launch(0,native_ready=True,holder_begin_ready=True,discovery_bad=True) is None
 assert a.jobs==old
 with pytest.raises(ValueError):a.view()

def test_actual_accepted_engine_canonical_no_EAM_alias():
 a=adapter();terminal(a,1)
 b=adapter();launch(b,1)
 assert not b.observe(1,idle=True,engine=0,token=12)
 with pytest.raises(ValueError):b.view()
 # X_ROM source has no AMAX endpoint; never qualify zero tie-offs.
 for x_me in (0,1):
  r=adapter(x_me=x_me,x_rom=1)
  assert not r.offer(1,slot=0,cmdpc=1737,engine=1,amax=1)
  with pytest.raises(ValueError):r.view()
 # Original engine0 is valid when X_ME=X_ROM=0.
 r=adapter(x_me=0);assert r.offer(1,slot=0,cmdpc=1737,engine=0,amax=1)

@pytest.mark.parametrize('bad', ['lease','slot','lane'])
def test_wrong_actual_ctl_query_cannot_publish(bad):
 a=adapter();begin=terminal(a,0);args=dict(lease=begin[0],slot=1,lane=0,ctlpc=2213)
 args[bad]+=1;assert a.ctl_offer(0,**args)
 with pytest.raises(ValueError):a.ctl_check(0)

def test_no_early_ctl_and_no_invalid_actual_result():
 a=adapter();begin=launch(a,1)
 assert not a.ctl_offer(1,lease=begin[0],slot=0,lane=0,ctlpc=2213)
 a.observe(1,idle=False,engine=1)
 assert not a.observe(1,idle=True,engine=1,token=0,valid=False)
 with pytest.raises(ValueError):a.view()

@pytest.mark.parametrize('qual',[dict(k=6),dict(bf16=1),dict(n=0),dict(op=1)])
def test_non_k1_actual_paths_not_substituted(qual):
 a=adapter();assert not a.offer(0,slot=1,cmdpc=1737,**qual)
 with pytest.raises(ValueError):a.view()

def test_no_multilane_underpriced_child():
 a=adapter();assert not a.offer(1,slot=0,lane=1,cmdpc=1737,engine=1,amax=1,m=2)
 with pytest.raises(ValueError):a.view()

def test_coded_qualifier_change_is_current_guarded():
 a=adapter();assert a.offer(0,slot=1,cmdpc=1737);a.arm(0)
 r=M.unpack(M.JOB,a.jobs[0]);r['k']=512;a.jobs[0]=M.pack(M.JOB,r)
 with pytest.raises(ValueError):a.launch(0,native_ready=True,holder_begin_ready=True)

@pytest.mark.parametrize('missing',['providers_idle','holders_empty','reverse_CDC_empty'])
def test_no_wrap_from_local_empty(missing):
 a=adapter();args=dict(lease=8191|(15<<21),receipts=63,providers_idle=True,holders_empty=True,reverse_CDC_empty=True);args[missing]=False
 assert not a.fence(**args)
 with pytest.raises(ValueError):a.view()

def test_continuous_40_cohorts_with_explicit_wrap_and_source_ctl_receipts():
 a=adapter()
 for it in range(40):
  c,j,q=a.view();lease=c['lease']
  for kind in (0,1):
   begin=terminal(a,kind)
   assert begin[0]==lease
   assert a.ctl_offer(kind,lease=lease,slot=begin[1],lane=0,ctlpc=2213)
   assert a.ctl_check(kind);assert a.finish_take(kind,ready=True)
   assert a.ctl_take(kind,lease=lease,ctlpc=2213,ready=True)
  assert a.fence(lease=lease,receipts=63,providers_idle=True,holders_empty=True,reverse_CDC_empty=True)
  # Same base position deliberately repeats after generation wrap; drain is explicit.
  assert a.rearm((8191,((lease>>21)+1)&15),7,accepted_leaf_start=True)

def test_k1_matches_full512_reference_beyond_512_candidates():
 rng=random.Random(58);scores=[(i,rng.choice([0,0x80000000,0x3f800000,0xbf800000,0x7f800000,0xff800000,rng.getrandbits(32)&0x7f7fffff]))for i in range(1100)]
 k=M.K1(len(scores))
 for i,b in scores:k.accept(i,b)
 assert k.publish()[0]==M.full512_reference(scores,1)[0]
 assert len(M.full512_reference(scores,512))==512

@pytest.mark.parametrize('winner',[65535,65536,100000,129279])
def test_actual_full_vocab_high_index(winner):
 k=M.K1(M.L.VOCAB)
 for i in range(M.L.VOCAB):k.accept(i,0x40000000 if i==winner else 0x3f800000)
 assert k.publish()==(winner,1,0)
 for _ in range(4):assert not k.take(False);assert k.output()==(winner,1,0)
 assert k.take(True)

@pytest.mark.parametrize('scores',[[0,0x80000000],[0x80000000,0],[0xff800000]*3,[0x7f800000]*3,[0x3f800000]*3,[0xbf800000,0xc0000000,0x80000001]])
def test_signedzero_ties_infinities_exact(scores):
 k=M.K1(len(scores))
 for i,b in enumerate(scores):k.accept(i,b)
 result=k.publish();assert result[0]==M.full512_reference(list(enumerate(scores)),1)[0]
 assert result[2]==int(scores[result[0]]==0xff800000)

def test_NaN_outside_source_contract_and_native_duplicates_refused():
 k=M.K1(2)
 with pytest.raises(ValueError):k.accept(0,0x7fc00000)
 k.accept(0,0)
 with pytest.raises(ValueError):k.accept(0,0)

@pytest.mark.parametrize('bit',range(72))
def test_k1_each_single_winner_fault_corrects_before_comparison(bit):
 k=M.K1(2);k.accept(0,0x3f800000);k.winner^=1<<bit;k.accept(1,0x40000000)
 assert k.publish()[0]==1

def test_k1_double_winner_fault_refuses_use():
 k=M.K1(2);k.accept(0,0);k.winner^=3
 with pytest.raises(ValueError):k.accept(1,0x3f800000)

def test_onepercent_segment_not_whole_token_claim():
 m=M.model();c=m['comparison']
 assert c['conditional_saved_edges_per_TOKX']==1535
 assert c['same_adapter_same_II_segment_rate_gain_pct']>1
 assert not c['whole_token_saving_qualified']
 assert json.loads((M.OUT/'model.json').read_text())==m

@pytest.mark.parametrize('bad',[dict(fault=1),dict(src=(1<<30)-1),dict(captured=3),dict(phase=2)])
def test_current_coded_K1_control_never_authorizes_use_or_consume(bad):
 k=M.K1(2);m=M.unpack(M.META,k.meta);m.update(bad);k.meta=M.pack(M.META,m)
 old=k.winner
 with pytest.raises(ValueError):k.accept(0,0)
 assert k.winner==old

def test_coded_K1_control_fault_blocks_heldoutput_discoveryedge():
 k=M.K1(1);k.accept(0,0);k.publish();old=k.out[:]
 m=M.unpack(M.META,k.meta);m['fault']=1;k.meta=M.pack(M.META,m)
 with pytest.raises(ValueError):k.take(True)
 assert k.out==old

def test_final_ledger_reuses_all_passed_functional_source_bodies_exactly():
 import ast,hashlib
 source=(M.ROOT/'tools/ds_mtp_native_k1_model.py').read_text()
 record=json.loads((M.OUT/'functional_gate_r2/record.json').read_text())
 nodes={n.name:hashlib.sha256(ast.get_source_segment(source,n).encode()).hexdigest()for n in ast.parse(source).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
 for name,seal in record['functional_source_seals'].items():assert nodes[name]==seal
 assert record['tests_passed']==119 and record['full_vocab_cases']==[65535,65536,100000,129279]

@pytest.mark.parametrize('kind,source_slot,dest',[(0,0,1),(0,6,7),(1,0,0),(1,7,7)])
def test_actual_native_IRQ_DSLOT_source_constructor(kind,source_slot,dest):
 a=adapter();assert M.source_frame_start(a,core_start_accepted=True,start_entry=2213,iter_entry=2213,leaf_cohort_accepted=True)=='ITER'
 assert M.source_offer(a,kind,source_slot=source_slot,cmdpc=2213,engine=kind,amax=kind)
 assert a.view()[1][kind]['slot']==dest
 assert a.arm(kind)
 begin=a.launch(kind,native_ready=True,holder_begin_ready=True)
 assert begin[1]==dest

def test_actual_draft_slot7_carry_is_refused_before_native_accept():
 a=adapter();M.source_frame_start(a,core_start_accepted=True,start_entry=2213,iter_entry=2213,leaf_cohort_accepted=True)
 assert not M.source_offer(a,0,source_slot=7,cmdpc=2213)
 assert M.unpack(M.JOB,a.jobs[0])['phase']==M.IDLE
 with pytest.raises(ValueError):a.view()

def test_actual_STEP_unpaired_AMAX_bypasses_no_owned_child():
 a=adapter();assert M.source_frame_start(a,core_start_accepted=True,start_entry=0,iter_entry=2213,leaf_cohort_accepted=False)=='BYPASS_AR'
 assert M.source_offer(a,1,source_slot=0,cmdpc=1737,engine=1,amax=1) is None
 assert a.view()[0]['used']==0 and a.view()[1][1]['phase']==M.IDLE

def test_no_ITER_child_before_accepted_source_start_and_leaf_cohort():
 a=adapter();assert M.source_frame_start(a,core_start_accepted=False,start_entry=2213,iter_entry=2213,leaf_cohort_accepted=True) is None
 assert M.source_offer(a,0,source_slot=0,cmdpc=1737) is None
 assert not M.source_frame_start(a,core_start_accepted=True,start_entry=2213,iter_entry=2213,leaf_cohort_accepted=False)
 with pytest.raises(ValueError):a.view()

def test_frame_mode_cannot_change_with_accepted_native_debt():
 a=adapter();M.source_frame_start(a,core_start_accepted=True,start_entry=2213,iter_entry=2213,leaf_cohort_accepted=True)
 assert M.source_offer(a,0,source_slot=0,cmdpc=1737)
 old=[x[:]for x in a.jobs]
 assert not M.source_frame_start(a,core_start_accepted=True,start_entry=0,iter_entry=2213,leaf_cohort_accepted=False)
 assert a.jobs==old
 with pytest.raises(ValueError):a.view()

def test_coded_frame_mode_singlefault_corrects_before_actual_source_route():
 a=adapter();M.source_frame_start(a,core_start_accepted=True,start_entry=2213,iter_entry=2213,leaf_cohort_accepted=True)
 # Last data bit of cohort48 is mode, translated through original systematic packing.
 a.c[0]^=1<<(M.L.POS[47]-1)
 assert M.source_offer(a,0,source_slot=0,cmdpc=1737)

def test_actual_start_entry_captured_then_guarded_header_nextedge():
 a=adapter();assert M.source_start_capture(a,core_start_accepted=True,start_entry=2213,iter_entry=2213)=='ITER_WAIT_HEADER'
 assert a.view()[0]['frame_pending']==1
 assert M.source_offer(a,0,source_slot=0,cmdpc=1737) is None
 assert not M.source_cohort_join(a,leaf_cohort_accepted=False,lease=8191|(15<<21),g=7)
 assert M.source_cohort_join(a,leaf_cohort_accepted=True,lease=8191|(15<<21),g=7)
 assert M.source_offer(a,0,source_slot=0,cmdpc=1737)

def test_coded_pending_singlefault_cannot_enable_early_native_child():
 a=adapter();M.source_start_capture(a,core_start_accepted=True,start_entry=2213,iter_entry=2213)
 a.c[0]^=1<<(M.L.POS[48]-1)
 assert M.source_offer(a,0,source_slot=0,cmdpc=1737) is None
 assert a.view()[0]['used']==0

def test_pending_accepted_start_is_owned_debt_not_localempty():
 a=adapter();M.source_start_capture(a,core_start_accepted=True,start_entry=2213,iter_entry=2213)
 assert not M.source_fence(a,lease=8191|(15<<21),receipts=63,providers_idle=True,holders_empty=True,reverse_CDC_empty=True)
 with pytest.raises(ValueError):a.view()

def test_reused_fullvocab_META_constant_and_source_codec_are_unchanged():
 import ast
 old=(M.OUT/'functional_gate_r2/ds_mtp_native_k1_model.py').read_text()
 new=(M.ROOT/'tools/ds_mtp_native_k1_model.py').read_text()
 def assigned(source,name):
  return next(ast.dump(n.value)for n in ast.parse(source).body if isinstance(n,ast.Assign)and any(isinstance(x,ast.Name)and x.id==name for x in n.targets))
 assert assigned(old,'META')==assigned(new,'META')
 assert M.model()['source_pins']==json.loads((M.OUT/'functional_gate_r2/model.json').read_text())['source_pins']
