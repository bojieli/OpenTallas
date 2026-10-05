"""Source-pinned K512/NW21 mutable-selector and native origin model; no RTL.

The logical-edge feedback cone is prospective: decode -> source comparison ->
encode. No physical timing or unpriced pipeline is inferred from codec tests.
"""
import argparse, collections, hashlib, json, math, struct
from pathlib import Path
import ds_mtp_accept_leaf_model as L
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/uarch/ds_mtp_protected_scalar_origin_20261003'
SOURCES=['rtl/hdc/v41/ot_hdc_select.sv','rtl/hdc/v41x/ot_hdc_v41x_xu_adapt.sv',
 'rtl/hdc/v41x/ot_hdc_v41x_me_adapt.sv','rtl/w17_runtime/hdc/v41x/ot_hdc_core_v41x.sv',
 'rtl/w17_runtime/chip/ot_chip_v41x_tile.sv','tools/hdc_program_v41.py',
 'rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv','rtl/experimental/ds_mtp_accept_20261003/ot_hdc_mtp_source_holders.sv',
 'tools/ds_mtp_accept_leaf_model.py',
 'results/uarch/ds_mtp_accept_leaf_20261003/inputs/results/uarch/w2_pc_exact_completion_20261003/inputs/cell_prices.json']

def inventory():
 # Separate independently updated source banks; no packing unrelated cells.
 return {'r0':(1,65),'key':(1,55),'wave':(8,64),'threshold':(8,64),
  'insertion_store':(512,55),'registered_pass':(511,55),'emission_bank':(512,23),
  'controller_output':(1,43), # source41 + stickyfault/admissionstop
  'pending_VM_read':(2,65), # two unbackpressured accepted-return reservations
  'VM_descriptor':(1,127), # src30/dst30/n21/k10/issued21/written10/phase3/pending2
  'native_origins':(2,54), # lease25/slot3/token21/phase3/seen_active1/fault1
  'cohort':(1,43)} # pos21/gen4/publishedTOKX8/AMAX8/stop1/fault1

def fp_key(bits):
 if bits & 0x7f800000 == 0x7f800000 and bits & 0x7fffff:
  raise ValueError('NaN outside original selector contract')
 if bits & 0x7fffffff == 0:return 0x80000000
 return (~bits & 0xffffffff) if bits>>31 else bits|0x80000000

def select(scores,k):
 """Source scalar lexicographic ordering, full indices, ORDER1; not RTL proof."""
 if not 0<=k<=512:raise ValueError('runtime k')
 if len({i for i,b in scores})!=len(scores):raise ValueError('duplicate source index')
 for i,b in scores:
  if not 0<=i<1<<21 or not 0<=b<1<<32:raise ValueError('source field bound')
 return sorted(i for i,b in sorted(scores,key=lambda p:(fp_key(p[1]),-p[0]),reverse=True)[:k])

class NativeOrigins:
 """Accepted native singleton ownership -> held finish, original lease only.

 Kind0 TOKX slot1..7; kind1 AMAX slot0..7. The matching provider is exclusive
 until finish handshake. Any source reset/fault quarantines accepted debt.
 Source ME intermediate ov is deliberately not a terminal event.
 """
 def __init__(self):
  self.words=[L.encode64(0),L.encode64(0)];self.cohort_word=L.encode64(0)
 def cohort_raw(self):
  raw,ce,ue=L.decode64(self.cohort_word)
  if ue or raw>>43:raise ValueError("poisoned cohort; all grants quarantined")
  return raw
 @property
 def fault(self):return bool((self.cohort_raw()>>42)&1)
 @fault.setter
 def fault(self,v):
  raw=self.cohort_raw();self.cohort_word=L.encode64(raw|(int(v)<<42))
 @property
 def cohort(self):
  raw=self.cohort_raw();return (raw&L.MASK,(raw>>21)&15) if (raw>>25)&65535 else None
 @property
 def used(self):
  mask=(self.cohort_raw()>>25)&65535
  return {(k,s) for k in range(2) for s in range(8) if mask>>(8*k+s)&1}
 def read(self,kind):
  raw,ce,ue=L.decode64(self.words[kind])
  if ue or raw>>54:self.fault=True;raise ValueError('poisoned origin')
  if raw>>53 or (raw>>49)&7>2 or (raw>>28)&L.MASK>=L.VOCAB:
   self.fault=True;raise ValueError('invalid origin semantic state')
  return {'lease':(raw&L.MASK,(raw>>21)&15),'slot':(raw>>25)&7,
   'token':(raw>>28)&L.MASK,'phase':(raw>>49)&7,'seen':bool((raw>>52)&1)}
 def write(self,kind,r):
  p,g=r['lease'];self.words[kind]=L.encode64(p|(g<<21)|(r['slot']<<25)|(r['token']<<28)|(r['phase']<<49)|(int(r['seen'])<<52))
 def fence(self,lease,*,allcopies=False,holders_empty=False,providers_idle=False):
  if not allcopies or not holders_empty or not providers_idle or any(self.read(k)['phase'] for k in range(2)):
   raise ValueError('positive original-lease/allcopies/holder/provider drain required')
  if self.cohort is not None and tuple(lease)!=self.cohort:raise ValueError('wrong cohort fence')
  if self.fault:raise ValueError('fault recovery not enrolled')
  self.cohort_word=L.encode64(0)
 def accept(self,kind,lease,slot,*,native_ready,holder_begin_ready):
  if self.fault or (self.cohort_raw()>>41)&1:return False
  r=self.read(kind);p,g=lease
  if r['phase'] or not native_ready or not holder_begin_ready:return False
  if not 0<=p<=L.MASK-slot or not 0<=g<16 or not (1 if kind==0 else 0)<=slot<8:
   self.fault=True;return False
  if self.cohort is not None and tuple(lease)!=self.cohort:
   self.fault=True;return False
  if (kind,slot) in self.used:self.fault=True;return False
  mask=(self.cohort_raw()>>25)&65535;mask|=1<<(8*kind+slot)
  self.cohort_word=L.encode64(p|(g<<21)|(mask<<25))
  self.write(kind,dict(lease=tuple(lease),slot=slot,token=0,phase=1,seen=False));return True
 def observe(self,kind,*,idle,token=0,intermediate_ov=False,source_fault=False,source_reset=False,result_valid=True):
  if self.fault:return None
  r=self.read(kind)
  if source_fault or source_reset:self.fault=True;return None
  if r['phase']!=1:return None
  if not idle:r['seen']=True;self.write(kind,r);return None
  if not r['seen']:return None # old idle on accepting edge is not completion
  if not result_valid or not 0<=token<L.VOCAB:self.fault=True;return None
  r['token']=token;r['phase']=2;self.write(kind,r);return self.output(kind)
 def output(self,kind):
  if self.fault:return None
  r=self.read(kind)
  return (r['lease'],r['slot'],r['token']) if r['phase']==2 else None
 def take(self,kind,echo,*,ready):
  out=self.output(kind)
  if out is None or not ready:return False
  if echo!=out:self.fault=True;return False
  self.words[kind]=L.encode64(0);return True

class ReadReservations:
 """Two fixed-latency native VM read slots, reserved before issue; no free ready."""
 def __init__(self):self.pending=[];self.completed=[]
 def issue(self,index):
  if len(self.pending)+len(self.completed)>=2:return False
  self.pending.append(index);return True
 def capture(self,value):
  if not self.pending:raise ValueError('unsolicited VM return')
  self.completed.append((self.pending.pop(0),value))
 def take(self,ready):return self.completed.pop(0) if ready and self.completed else None

def tree(n,fanout):
 levels=[]
 while n>1:n=math.ceil(n/fanout);levels.append(n);fanout=8
 return levels

def model():
 pins=json.loads((OUT/'input_manifest.json').read_text())
 for row in pins:
  assert hashlib.sha256((ROOT/row['path']).read_bytes()).hexdigest()==row['sha256'],row['path']
  assert hashlib.sha256((OUT/row['archive']).read_bytes()).hexdigest()==row['sha256']
 src=(ROOT/SOURCES[1]).read_text();prog=(ROOT/SOURCES[5]).read_text()
 assert '.IW(16)' in src and '.in_idx(s_idx[15:0])' in src
 assert 'not f.get("me_amax", 0)' in prog
 inv=inventory();raw=sum(n*b for n,b in inv.values());words=sum(n*math.ceil(b/64) for n,b in inv.values());bits=72*words
 prices=json.loads((ROOT/SOURCES[-1]).read_text())['facts'];sections={}
 g=L.Gates()
 for _ in range(words):g.codec()
 g.OR(sum(n*(math.ceil(b/64)*64-b) for n,b in inv.values()));g.OR(words-1)
 sections['all_current_codecs_padding_and_joint_fault_reduction']=g.dict()
 g=L.Gates();g.nand(12*(512*54+511*21));g.inv(8*(512*54+511*21))
 g.mux(55*512,2);g.mux(55*511,2);g.mux(23*512,4);g.inv(21*512)
 sections['source_insertion_sort_and_bank_update_construction']=g.dict()
 g=L.Gates()
 for _ in range(6):g.eq(25);g.eq(3)
 for _ in range(4):g.lt_const(21,L.VOCAB)
 g.add(30);g.add(21);g.add(10);g.mux(130,2);g.mux(127+108+43,8)
 g.AND(128);g.OR(128);g.const_eq(6,63)
 sections['read_reservations_address_counts_identity_held_output_and_fence']=g.dict()
 reset=tree(bits,7);clock=tree(bits,8)
 sections['storage_QN_restore_hold_clock_reset_lower_bound']={
 'DFFASRHQNx1_ASAP7_75t_R':bits,'INVx1_ASAP7_75t_R':2*bits,
 'NAND2x1_ASAP7_75t_R':3*bits,'BUFx4_ASAP7_75t_R':2*bits+sum(reset)+sum(clock)}
 # Conservative registered-source fanout trees for global freeze/fault, sort phases,
 # threshold, descriptor and origin fields. Actual routed trees not inferred.
 sections['global_and_descriptor_fanout_minimum']={'BUFx4_ASAP7_75t_R':4*L.buffers(bits)+10*L.buffers(512)+127*L.buffers(2)}
 total=collections.Counter()
 for counts in sections.values():total.update(counts)
 body=sum(n*prices[c]['SS']['area_um2'] for c,n in total.items())
 return dict(schema='DS_MTP_PROTECTED_SCALAR_NATIVE_ORIGIN_R1',base='6c67ab4f7afc106dc21ca5dd4447097d4f4d8adc',default_enable=False,
 selected_scope='one fullK512 FP32 NW21 ORDER1 scalar + two serial native origins, ClassA greedy only',
 source_pins=pins,inventory={k:dict(records=n,raw_bits_per_record=b,words_per_record=math.ceil(b/64))for k,(n,b)in inv.items()},
 state=dict(source_scalar_raw_21=69226,source_scalar_raw_16=61536,width_delta_only=7690,raw_bits=raw,codewords=words,protected_bits=bits,source_controller_raw=41,controller_added_stop_fault_bits=2,r0_two_words_atomic=True,independent_word_debt_not_packed_across_cells=True),
 ports=dict(MACs_per_cycle=0,VM_read_bytes_per_edge=4,VM_write_bytes_per_edge=4,score_stream_payload_bits=64,score_stream_signals=66,index_stream_payload_bits=23,index_stream_signals=25,VM_read_request_signals=31,VM_read_return_signals=32,VM_write_signals=63,producer_cuts=[52,52],original_lease_input_signals=30,fence_signals=33,coded_storage_simultaneous_read_words=words,coded_storage_writers_max_upper=words,coded_storage_kind='FF registers with independent update, NOT singleported macro',VM_reservations=2,source_VM_fixed_latency_enrolled=False,legal_channel_capacity=None,channels_and_CDC_installed=False),
 cost=dict(cell_counts_by_section=sections,cell_counts_total=dict(sorted(total.items())),gross_body_um2=body,gross50pct_mm2=body/.5/1e6,reset_levels_minimum=reset,clock_levels_minimum=clock,reset_leaf_max_fanout=7,reset_limit_fF=5.76,reset7pin_fF=7*prices['DFFASRHQNx1_ASAP7_75t_R']['FF']['pins']['RESETN']['cap_fF'],actual_wire_sites=None,matched_existing_scalar_debit=None,net_area=None,actual_S58_PAR2_home_and_replicas=None,requested_slot='Arch/Maxwell serial spine full protectedK512 scalar + native origin',reserved=False),
 calendar=dict(source_after_last_edges=1026,prospective_after_last_edges=1026,VM_return_pending_reservations=2,source_emit_bank_cycles=512,source_emit_post_first_tail_edges=511,source_draft_vocab=129280,source_one_draft_segment_accepted_scores_plus_tail_edges=130817,source_segment_ideal_ns_at_point9=130817/.9,source_segment_scope='lower bound excluding VM issue/capture, native terminal, holder waits and actual clock; charge one observed draft segment at a time, no invented iteration count',logical_tick_II=1,loaded_feedback_cone='decode64 -> original FP32/insertion/sort logic -> encode64 -> coded feedback; unmeasured',prospective_clock_GHz=.9,SS_setup_ps=60,FF_hold_ps=25,SS_FF_closed=False,output_backpressure='freeze ALL scalar banks/waves/controller on held output; source has no ready, new optin handshake and VM issue reservation mandatory',original_source_schedule_compatible_without_adapter=False,extra_pipeline_stages_selected=0,extra_pipeline_if_required='FAIL admission; reprice every intermediate ownership/data word, new feedback II and full segment calendar before RTL',per_user='for each observed segment charge actual accepted score edges +1026 post-last + held output waits + terminal/holder handshake; no free overlap or invented MTP iteration count',whole_iteration_latency=None),
 native_contract=dict(acceptance='joint native go&&ready and protected holder begin-ready at same accepted command; no isolated pulses',TOKX='active nonzero-vocab FP32 OP_SEL runtimek1 accepted XU command; compiler off/n0 descriptors must not allocate child;  descriptor/originallease/TOKXdest=c_dslot+1 bounds checked before grant; store full21 first scalar result; finish only after active then drained XU terminal',AMAX='accepted me_go&&me_ready&&i_amax actual EAM engine; source program excludes AMAX batching; final am_idx plus am_any valid only after active then drained idle, never intermediate ov',MP='source default1; actual selected overrides must be enrolled; no free8lane assumption',lease_source='existing guarded accept .lease=decoded header key after acceptedstart, guarded by !fault; no command on sameedge start; installed native connection missing',lease='private accepted pos21/gen4/slot3; provider cannot accept another samekind command before held matching finish handshake',repeated_tuple='per-kind8bit published mask prohibits samekind/slot twice in cohort; no reuse/reset/wrap without matching positive allcopies+holder+provider fence',generation='4bit sourcecompatible, not1bit; positive allcopies/reverseCDC drain obligation not inferred from local emptiness',holder_consumption='local source delivery only; NOT KV rollback/tag retirement',reset='source reset/fault during accepted debt quarantines it; cold reset externally positive allcopies fenced only',source_XU_ME_descriptor_and_upstream_controls_protected=False),
 admission=dict(model_inventory_and_ownership_ready=True,RTL_authorized_by_this_model=False,missing=['loaded decode/compare/encode SS/FF cut decision','Arch actual slot/tree/channel/clock enrollment','actual native VM fixed read return timing and freeze/issue adapter','source XU/ME descriptor, command lease producer and upstream mutable control protection','whole-program provider/holder/reverseCDC positive drain receipts'],whole_MTP_qualified=False,rate_or_tau_adopted=False,build_or_P_and_R=False))

def main():
 p=argparse.ArgumentParser();p.add_argument('--verify',action='store_true');p.add_argument('--out',type=Path);a=p.parse_args()
 data=(json.dumps(model(),indent=2,sort_keys=True)+'\n').encode();dest=a.out or OUT/'model.json'
 if a.verify:assert dest.read_bytes()==data;print('PASS source pins and byteexact protected scalar/native model')
 else:dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data);print(dest)
if __name__=='__main__':main()
