#!/usr/bin/env python3
"""One source-compatible full-width greedy prefix leaf; model only, no RTL/run.

Word layout is the existing W6 mutable encode64/decode64 ABI. Positive external
allcopies fencing is an input obligation, never inferred from local empty.
"""
from pathlib import Path
import argparse,collections,hashlib,json,math
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/uarch/ds_mtp_accept_leaf_20261003'
POS=[p for p in range(1,72) if p&(p-1)]
NW=21; NSLOT=8; VOCAB=129280; MASK=(1<<21)-1
FIELDS={**{f'{kind}{s}':[('token',21),('valid',1)] for kind in ('s','t') for s in range(8)},
 'header':[('pos',21),('gen',4),('g',3),('phase',3),('stop',1),('corrected',1)],
 'fault':[('bad',1)],'result':[('a',3),('done',1),('any',1),('n',4),('bonus',21)],
 'aq':[('pos',21),('gen',4),('g',3),('valid',1)],
 'sq':[('pos',21),('gen',4),('slot',3),('token',21),('valid',1)],
 'tq':[('pos',21),('gen',4),('slot',3),('token',21),('valid',1)],
 'fq':[('pos',21),('gen',4),('receipts',6),('valid',1),('rearm',1)],
 'match':[('pos',21),('gen',4),('g',3),('valid',1),('bits',7)]}
IDLE,COLLECT,REDUCE,GUARD,OUTPUT,DRAIN,FAULT=range(7)
def encode64(x):
 if not 0<=x<1<<64:raise ValueError('data64 bounds')
 c=sum(((x>>i)&1)<<(p-1) for i,p in enumerate(POS))
 for k in range(7):
  parity=sum((c>>(p-1))&1 for p in range(1,72) if p&(1<<k) and p!=1<<k)&1
  c|=parity<<((1<<k)-1)
 return c|((c.bit_count()&1)<<71)
def decode64(c):
 if not 0<=c<1<<72:raise ValueError('code72 bounds')
 syndrome=0
 for k in range(7):syndrome|=(sum((c>>(p-1))&1 for p in range(1,72) if p&(1<<k))&1)<<k
 overall=c.bit_count()&1;ue=bool(syndrome and (not overall or syndrome>71));corrected=False
 if syndrome and overall and syndrome<=71:c^=1<<(syndrome-1);corrected=True
 elif not syndrome and overall:c^=1<<71;corrected=True
 data=sum(((c>>(p-1))&1)<<i for i,p in enumerate(POS))
 return data,corrected,ue
def pack(name,values):
 x=shift=0
 for key,n in FIELDS[name]:
  v=values.get(key,0)
  if type(v) is not int or not 0<=v<1<<n:raise ValueError('field '+key)
  x|=v<<shift;shift+=n
 return encode64(x)
def unpack(name,code):
 raw,corrected,ue=decode64(code);shift=0;r={}
 for key,n in FIELDS[name]:r[key]=(raw>>shift)&((1<<n)-1);shift+=n
 # Zero padding is part of the valid mutable record; refuse legal-codeword corruption there.
 ue=ue or bool(raw>>shift)
 return r,corrected,ue
class Leaf:
 def __init__(self,*,cold_fenced=False):
  if not cold_fenced:raise ValueError('external cold allcopies/reset fence required')
  self.words={k:pack(k,{}) for k in FIELDS};self.cycle=0
 def view(self):return {k:unpack(k,c)[0] for k,c in self.words.items()}
 @property
 def lease(self):
  h=self.view()['header'];return h['pos'],h['gen']
 def inject(self,name,*bits):
  for bit in bits:self.words[name]^=1<<bit
 def cold_reset(self,*,allcopies_fenced=False):
  if not allcopies_fenced:raise ValueError('cold reset fence missing')
  v=self.view()
  if v['header']['phase']!=IDLE or any(v[k]['valid'] for k in FIELDS if k.startswith(('s','t'))):raise ValueError('owned debt cannot reset')
  self.words={k:pack(k,{}) for k in FIELDS}
 def step(self,**e):
  """Old-state tick. Input holders accept independently at most1/2edges.

  Returned accepted names are handshakes, not provider/KV retirement receipts.
  Any discovered malformed accepted event or uncorrectable state blocks all
  normal grants/retirement on the discovery edge. Fault preserves prior debt.
  """
  self.cycle+=1;old=self.view();n={k:dict(v)for k,v in old.items()};h=old['header'];accepted=[];bad=False
  decoded=[unpack(k,c) for k,c in self.words.items()]
  if any(x[2] for x in decoded) or old['fault']['bad']:bad=True
  if h['phase']>DRAIN or h['pos']>MASK-h['g']:bad=True
  if any(old[f'{kind}{slot}']['token']>=VOCAB for kind in ('s','t') for slot in range(8)):bad=True
  if h['phase'] in (GUARD,OUTPUT,DRAIN):
   rr=old['result']
   if rr['a']>h['g'] or rr['n']!=rr['a']+1 or rr['bonus']>=VOCAB or rr['any']!=1:bad=True
  def fail():
   self.words['fault']=pack('fault',{'bad':1})
   # Preserve all encoded input/output/ownership state, including an invalid header.
   return {'accepted':[],'fault':True,'out_valid':False,'cycle':self.cycle}
  if e.get('caller_bad'):bad=True
  if bad:return fail()
  n['header']['corrected']|=int(any(x[1] for x in decoded))
  if e.get('stop'):n['header']['stop']=1
  # Validate ALL presented events against old state first; bad blocks a concurrent consume.
  for event,bank,kind in [('tokx','sq','s'),('amax','tq','t')]:
   if event in e and not h['stop'] and h['phase']==COLLECT and not old[bank]['valid']:
    lease,slot,token=e[event]
    if tuple(lease)!=(h['pos'],h['gen']) or type(slot)is not int or not 0<=slot<=h['g'] or (kind=='s' and slot==0) or type(token)is not int or not 0<=token<VOCAB or old[f'{kind}{slot}']['valid']:bad=True
  if 'accept' in e and not h['stop'] and h['phase']==COLLECT and not old['aq']['valid']:
   lease,g=e['accept']
   if tuple(lease)!=(h['pos'],h['gen']) or g!=h['g']:bad=True
  if 'consume' in e and h['phase']==OUTPUT and tuple(e['consume'])!=(h['pos'],h['gen']):bad=True
  if 'fence' in e and h['phase']==DRAIN:
   lease,receipts=e['fence']
   if tuple(lease)!=(h['pos'],h['gen']) or receipts!=63:bad=True
  if 'start' in e and h['phase']==IDLE:
   pos,token,g=e['start']
   if not all(type(x)is int for x in (pos,token,g)) or not 0<=g<8 or not 0<=pos<=MASK-g or not 0<=token<VOCAB:bad=True
  if bad:return fail()
  if 'start' in e and h['phase']==IDLE and not h['stop']:
   pos,token,g=e['start'];n={k:{key:0 for key,b in fields}for k,fields in FIELDS.items()}
   n['header'].update(pos=pos,gen=(h['gen']+1)%16,g=g,phase=COLLECT);n['s0']=dict(token=token,valid=1);accepted.append('start')
  # Source updates require an active lease; a non-backpressured event before start is bad.
  elif any(k in e for k in ('tokx','amax','accept')) and h['phase']==IDLE:return fail()
  for event,bank,kind in [('tokx','sq','s'),('amax','tq','t')]:
   if event in e and h['phase']==COLLECT and not h['stop'] and not old[bank]['valid']:
    lease,slot,token=e[event];n[bank]=dict(pos=lease[0],gen=lease[1],slot=slot,token=token,valid=1);accepted.append(event)
   if old[bank]['valid']:
    q=old[bank];slot=q['slot']
    if (q['pos'],q['gen'])!=(h['pos'],h['gen']) or h['phase']!=COLLECT or slot>h['g'] or (kind=='s' and slot==0) or q['token']>=VOCAB or old[f'{kind}{slot}']['valid']:return fail()
    n[f'{kind}{slot}']=dict(token=q['token'],valid=1);n[bank]['valid']=0
  if 'accept' in e and h['phase']==COLLECT and not h['stop'] and not old['aq']['valid']:
   lease,g=e['accept'];n['aq']=dict(pos=lease[0],gen=lease[1],g=g,valid=1);accepted.append('accept')
  if old['aq']['valid']:
   q=old['aq']
   # Never allow newest same-edge writes to satisfy required freshness.
   if old['sq']['valid'] or old['tq']['valid']:pass
   elif h['phase']!=COLLECT or (q['pos'],q['gen'])!=(h['pos'],h['gen']) or q['g']!=h['g'] or not all(old[f's{i}']['valid'] for i in range(h['g']+1)) or not all(old[f't{i}']['valid'] for i in range(h['g']+1)):return fail()
   else:
    bits=sum(int(old[f's{i+1}']['token']==old[f't{i}']['token'])<<i for i in range(h['g']))
    n['match']=dict(pos=h['pos'],gen=h['gen'],g=h['g'],valid=1,bits=bits);n['aq']['valid']=0;n['header']['phase']=REDUCE
  if h['phase']==REDUCE:
   m=old['match']
   if not m['valid'] or (m['pos'],m['gen'],m['g'])!=(h['pos'],h['gen'],h['g']):return fail()
   a=0
   while a<h['g'] and (m['bits']>>a)&1:a+=1
   n['result']=dict(a=a,done=0,any=1,n=a+1,bonus=old[f't{a}']['token']);n['match']['valid']=0;n['header']['phase']=GUARD
  if h['phase']==GUARD:n['result']['done']=1;n['header']['phase']=OUTPUT
  if h['phase']==OUTPUT:
   n['result']['done']=0
   if 'consume' in e:n['header']['phase']=DRAIN;accepted.append('consume')
  if h['phase']==DRAIN and 'fence' in e:
   lease,receipts=e['fence'];n['fq']=dict(pos=lease[0],gen=lease[1],receipts=receipts,valid=1,rearm=0);accepted.append('fence')
  if old['fq']['valid']:
   if h['phase']!=DRAIN or (old['fq']['pos'],old['fq']['gen'])!=(h['pos'],h['gen']) or old['fq']['receipts']!=63:return fail()
   for k in FIELDS:
    if k.startswith(('s','t')) or k in ('aq','match','fq'):n[k]={key:0 for key,b in FIELDS[k]}
   n['header']['phase']=IDLE
  # Runtime rearm changes admission_stop only in IDLE, after a previous matched fence.
  if 'rearm' in e:
   if h['phase']!=IDLE or not h['stop'] or e['rearm']!=63:return fail()
   n['header']['stop']=0;accepted.append('rearm')
  for k in FIELDS:
   if n[k]!=old[k]:self.words[k]=pack(k,n[k])
  v=self.view();r=v['result'];phase=v['header']['phase']
  return dict(accepted=accepted,fault=False,out_valid=phase==OUTPUT,result=r,frame=[v[f't{i}']['token']for i in range(8)],lease=self.lease,cycle=self.cycle)

class CallerAdapter:
 """Prospective sourceX_SEL20->21 and origin holder reference; no RTL adapter.

 Shared source c_slot_r stays frozen in the sequencer while this command is
 held, so it is an existing source register, not an unpriced extra slot bank.
 Upstreamfault drives leaf caller_bad jointly with other events.
 """
 def __init__(self):self.words={'select':encode64(0),'tok_origin':encode64(0),'amax_origin':encode64(0)}
 def capture_select(self,index20,lease):
  if type(index20)is not int or not 0<=index20<VOCAB:raise ValueError('full20 selector bounds')
  self.words['select']=encode64(index20)
  self.capture_origin('tok_origin',lease)
 def capture_origin(self,kind,lease):
  pos,gen=lease
  if not 0<=pos<1<<21 or not 0<=gen<16:raise ValueError('full25 lease bounds')
  raw,corrected,ue=decode64(self.words[kind])
  if ue or raw>>26 or (raw>>25)&1:raise ValueError('origin holder busy or poisoned')
  self.words[kind]=encode64(pos|(gen<<21)|(1<<25))
 def inspect(self):
  r={};bad=False
  for k,c in self.words.items():
   raw,corrected,ue=decode64(c);bits=21 if k=='select' else 26
   bad|=bool(ue or raw>>bits);r[k]=raw
  bad|=r['select']>=VOCAB
  return r,bad
 def tokx(self,source_frozen_slot):
  r,bad=self.inspect();o=r['tok_origin']
  if not (o>>25)&1:bad=True
  return {'caller_bad':bad,'tokx':((o&MASK,(o>>21)&15),source_frozen_slot,r['select'])}
 def release_origin(self,kind,*,matching_handshake):
  r,bad=self.inspect()
  if bad or not matching_handshake:raise ValueError('no matching source handshake')
  self.words[kind]=encode64(r[kind]&((1<<25)-1))

# Fully enumerated NAND/INV construction, not the earlier assumed768 gates/word.
class Gates:
 def __init__(self):self.c=collections.Counter()
 def inv(self,n=1):self.c['INVx1_ASAP7_75t_R']+=n
 def nand(self,n=1):self.c['NAND2x1_ASAP7_75t_R']+=n
 def xor(self,n=1):self.nand(4*n)
 def AND(self,n=1):self.nand(n);self.inv(n)
 def OR(self,n=1):self.nand(n);self.inv(2*n)
 def eq(self,n):self.xor(n);self.inv(n);self.AND(n-1)
 def const_eq(self,n,v):self.inv(n-v.bit_count());self.AND(n-1)
 def mux(self,bits,branches):self.nand(3*bits*(branches-1));self.inv(branches-1)
 def lt_const(self,n,c):
  # msb-to-lsb recurrence lt=(not a AND (equal_prefix/constant)) OR prefix; no CSE.
  for i in range(n):self.inv();self.AND(2);self.OR()
 def add(self,n):self.xor(2*n);self.AND(2*n);self.OR(n)
 def codec(self):
  groups=[[p for p in POS if p&(1<<k)]for k in range(7)]
  self.xor(sum(len(g)-1 for g in groups)+70) # seven check XOR trees +overall71
  syn_groups=[[p for p in range(1,72)if p&(1<<k)]for k in range(7)]
  self.xor(sum(len(g)-1 for g in syn_groups)+71)
  for p in POS:self.const_eq(7,p);self.AND();self.xor() # overall&hit, data^flip
  self.lt_const(7,72);self.const_eq(7,0);self.OR(6);self.AND(3);self.OR(2);self.inv(2) # UE/corrected classification
 def dict(self):return dict(sorted(self.c.items()))
def buffers(sinks):
 total=0
 while sinks>1:sinks=math.ceil(sinks/8);total+=sinks
 return total

def model():
 pins=json.loads((OUT/'input_manifest.json').read_text())
 for r in pins:
  assert hashlib.sha256((OUT/r['archive']).read_bytes()).hexdigest()==r['sha256'],r['path']
 prices=json.loads((OUT/'inputs/results/uarch/w2_pc_exact_completion_20261003/inputs/cell_prices.json').read_text());facts=prices['facts']
 sections={};g=Gates()
 for _ in range(7):g.eq(21)
 sections['seven_fullwidth_prefix_comparisons']=g.dict()
 g=Gates();g.AND(7);g.OR(7);g.add(4);g.mux(21,8);g.mux(3,8);sections['prefix_count_bonus_selection']=g.dict()
 g=Gates()
 for _ in range(6):g.eq(25)
 for _ in range(20):g.lt_const(21,VOCAB) # all16 slotdata +3 presented tokens+resultbonus
 for _ in range(2):g.lt_const(3,8);g.eq(3);g.const_eq(3,0);g.mux(1,8)
 g.eq(3);g.eq(4);g.add(22);g.const_eq(3,7)
 for _ in range(2):
  for slot in range(8):g.const_eq(3,slot)
 for slot in range(8):g.const_eq(3,slot)
 g.OR(28);g.AND(16);g.OR(16);g.AND(14)
 sections['identity_bounds_freshness_and_slotwrite_decode']=g.dict()
 g=Gates()
 for phase in range(7):g.const_eq(3,phase)
 g.const_eq(6,63);g.add(4)
 controls={'start_capture':6,'tokx_capture':8,'amax_capture':8,'accept_capture':7,
 'consume_matching_held':4,'fence_capture':5,'fence_commit':5,'idle_rearm':5,
 'sq_publish':7,'tq_publish':7,'fresh_match_snapshot':8,'match_to_result':4,
 'result_guard':4,'stop_latch':2,'result_done_clear':2}
 for arity in controls.values():g.AND(arity-1)
 # Presented semantic failure in eligible port; registeredquery failure; result/header legality.
 fault_terms={'start_bounds':4,'tokx_semantics':5,'amax_semantics':5,'accept_semantics':5,
 'wrong_result_ack':3,'wrong_fence':3,'sq_bad':2,'tq_bad':2,'aq_bad':3,
 'match_bad':2,'result_bad':3,'header_bad':2,'rearm_bad':2}
 for arity in fault_terms.values():g.AND(arity-1);g.inv()
 g.OR(len(fault_terms)-1);g.OR(3);g.inv(16)
 sections['state_stop_reset_fence_heldoutput_and_source_adapter']=g.dict()
 raw=sum(sum(b for k,b in fields) for fields in FIELDS.values());assert raw==614
 words=len(FIELDS);assert words==24
 # Source XU select21 +two captured origin lease25/valid1 records. Existing16select is matched debit only.
 caller_raw=21+2*26;caller_words=3;protected=(words+caller_words)*72
 g=Gates()
 for _ in range(words+caller_words):g.codec()
 # Check zero padding and decoded legal fields on each of27 independently protected records.
 g.OR(sum(64-sum(b for k,b in fields) - 1 for fields in FIELDS.values())+(64-21-1)+2*(64-26-1));g.OR(words+caller_words-1)
 sections['exact_W6_codec_encode_decode_and_padding_refusal']=g.dict()
 g=Gates()
 # One explicit8:1 raw-update mux per record bit covers old/current/reset/start/query/result/fence/control sources.
 # This is a finite conservative no-CSE construction, not a prediction of synthesized sharing.
 for name,fields in FIELDS.items():g.mux(sum(b for key,b in fields),8)
 for bits in (21,26,26):g.mux(bits,8)
 sections['raw_record_update_selectors_max8_sources_each']=g.dict()
 sections['protected_storage_QN_restore_hold_feedback']={'DFFASRHQNx1_ASAP7_75t_R':protected,'INVx1_ASAP7_75t_R':2*protected,'NAND2x1_ASAP7_75t_R':3*protected,'BUFx4_ASAP7_75t_R':2*protected}
 # Eight leafs per bus; two input streams/token+identity and two decoded output arrays.
 fanout_bits=2*50+2*168+25+3+1
 fanout_tree=(2*50+2*168)*buffers(8)+(25+3+1)*buffers(32)
 global_hold_buffers=buffers(protected+336+len(controls))
 sections['clock_reset_and_eight_input_fanout']={'BUFx4_ASAP7_75t_R':2*buffers(protected)+fanout_tree+buffers(words+caller_words)+global_hold_buffers}
 totals=collections.Counter()
 for s in sections.values():totals.update(s)
 body=sum(n*facts[c]['SS']['area_um2']for c,n in totals.items())+protected*prices['TIEHI_body_um2']
 leafports={
  'start':{'payload_bits':45,'signal_bits':47,'max_accept_per_edge':1},
  'tokx':{'payload_bits':49,'signal_bits':51,'nominal_II_edges':2},
  'amax':{'payload_bits':49,'signal_bits':51,'nominal_II_edges':2},
  'accept':{'payload_bits':28,'signal_bits':30,'max_occupied':1},
  'result':{'payload_bits':221,'signal_bits':250,'max_occupied':1,'held_until_matching_ready':True,'definition':'ttok168,a3,n4,bonus21,sharedlease25; out_v/acc_done/acc_any3 plus acklease25+ready1'},
  'source_stok':{'payload_bits':168,'signal_bits':168,'slots':8,'value_bits_per_slot':21,'ttok_alias':'result ttok168 is same physical bus, counted once'},
  'fence':{'payload_bits':32,'signal_bits':34,'mask_bits':6,'positive_receipts_required':63},
  'clock_reset_stop_fault_corrected':{'payload_bits':0,'signal_bits':5}}
 tracks=sum(p['signal_bits'] for p in leafports.values())
 model=dict(schema='DS_MTP_ACCEPT_FULLWIDTH_MODEL_R1',candidate='NSLOT8_NW21_GREEDY_PREFIX_BONUS_ONE_COHORT',opt_in_default=False,class_A='Current source greedy only; no stochastic sampling or KV rollback implementation',MACs_per_cycle=0,
  source_baseline_raw_FF=366,raw_leaf_state_bits=raw,raw_caller_select_and_stamp_bits=caller_raw,raw_total_bits=raw+caller_raw,
  protected_leaf_words=words,protected_caller_words=caller_words,protected_total_bits=protected,
  state_layout=FIELDS,caller_layout={'select':21,'tokx_origin_and_held_v':26,'amax_origin_and_held_v':26},
  protection={'codec':'source W6 interleaved Hamming64/72,7syndrome+overall; decoded padding/bounds checked','independent_codewords':words+caller_words,'encoder_and_decoder_replicas':words+caller_words,'corrected_data_bits_per_decoder':64,'codeword_bits_per_decoder':72,'planned_768_gate_shortcut_used':False,'single_error':'correct before any use; correction flag; no mandatory background scrub','double_or_invalid_syndrome':'joint-oldstate quarantine, no normal grant/output/debt release','decoded_control_error_gating':'all27 codewords+padding+semanticbounds; positive fences cannot clear owned fault debt','codec_is_installed':False},
  ports=leafports,port_bytes_per_edge={k:v['payload_bits']/8 for k,v in leafports.items()},service_boundary_signal_tracks_required=tracks,global_PHY_capacity_credit=0,
  slot_identity={'fields':{'pending_base_position':21,'leaf_owned_generation':4,'slot':3},'core_instance_context':'implicit only inside actual selected core; shared multi-client fabric not supported','generation_allocated':'increment modulo16 only after previous matched six-receipt fence, exported25-bit lease echoed by every producer/result/fence','no_width_truncation':True,'wrap_reset_proof':'positive old copies absent including core/XU/ME/readers/pipelines and forward/return/reverse; local empty never sufficient','wrap_stall_bound_edges':None},
  controller_conjunction_arities=controls,controller_fault_term_arities=fault_terms,
  cell_counts_by_section=sections,cell_counts_total=dict(totals),gross_cell_body_um2=body,gross_at_50pct_util_mm2=body/0.5/1e6,area_scope='constructive allowed-cell unmapped screen, exact stated gate construction incl no-CSE conservative bounds/controls; actual synth may differ',
  matched_baseline_debit={'raw_accept_state_bits':366,'old_XU_select_bits':16,'actual_cell_overlap_and_net_area':None,'rule':'gross new leaf/caller state replaces exact matched old controller/select only after source union; do not blindly add366 or subtract shared VM/provider'},
  clock={'service_domain':'serial-chain prospective0.9GHz','period_ps':1e12/0.9e9,'setup_uncertainty_ps':60,'hold_uncertainty_ps':25,'functional_enrollment':'one clock, synchronous valid/ready endpoints, no false/multicycle bypass','SS_FF_loaded_closure':False,'stage_plan':'querycapture -> checkedfreshness+protectedmatch -> prefix/bonus encodedresult -> protectedresultguard;3addedleafedges after accept handshake','accept_to_acc_done_min_edges':3,'old_source_accept_min_edges':1,'added_vs_leaf_min_edges':2,'added_min_serial_ns':2/0.9,'fence_and_result_backpressure_edges':None,'L1_protected_cones_proven':False,'stage_change_rule':'Any added protection/prefix stage must add72-bit record/codecs/cuts and its edges before RTL change; no unpricedL2/L3 fallback'},
  clock_load={'protected_FF_sinks':protected,'SS_unbuffered_clock_fF':protected*facts['DFFASRHQNx1_ASAP7_75t_R']['SS']['pins']['CLK']['cap_fF'],'FF_unbuffered_clock_fF':protected*facts['DFFASRHQNx1_ASAP7_75t_R']['FF']['pins']['CLK']['cap_fF'],'fanout_branch':8,'clock_plus_reset_buffers':2*buffers(protected),'feedback_twoBUF_perbit':True,'eight_leaf_broadcast_bits':2*50+2*168,'header_and_gamma_fault_broadcast_bits':29,'header_fanout_sinks_budget':32,'global_hold_release_buffer_count':global_hold_buffers,'actual_arrival_slew_load_skew':None},
  physical_slot={'requested_owner_slot':'MTP_ACCEPT_SERIAL_SPINE_PER_ACTUAL_CORE','replicas_per_enrolled_core':1,'ROM_and_HBM_replica_count':'caller/source selection pending; no free fullfleet replication','minimum_50pct_cell_area_mm2':body/0.5/1e6,'minimum_signal_corridor_um_at_48nm_pitch':tracks*.048,'actual_reserved_rectangle':None,'actual_legal_channel_tracks':None,'PG_clock_via_exclusions':None,'fit_qualified':False,'component_rectangle_request':'ceil(cell_area_at50pct/128um) height rounded to0.27um rows, minimum width128um; unreserved request only','requested_width_um':128,'requested_height_um':math.ceil(body/0.5/128/0.27)*0.27},
  admission={'prospective_finite_functional_model':'READY_FOR_PARENT_LEAF_ENROLLMENT_REVIEW','RTL_or_P_and_R_authorized_by_this_receipt':False,'physical_G0':'PENDING_NAMED_SLOT_CHANNEL_CLOCK_AND_STAGE_ENROLLMENT','source_connected':'FAIL_CURRENT_TOKX16_AND_PULSE_ONLY_CALLER_NEEDS_ADAPTER','TOKX_source_legal_branch':'X_SEL full selector IW20 may zeroextend toNW21 only after sel_first/core wire widening; X_SEL0 legacy scalarIW16 remains unsupported/unpriced for fullvocab','whole_MTP':'UNQUALIFIED','missing_whole_drafter_blocks_separate_leaf':False,'rate':None},source_pins=pins,
  source_kernel_join={'TOKX':'core d_ctl1 c_slot_r -> XU fullX_SEL20b index ->21b selectedtoken holder; current sel_first16 truncation must be removed, no zeroextension of truncated16 permitted','AMAX':'core d_ctl2 am_idx_v[d_clane*NW+:NW] already21bits, captured origin lease required','ACCEPT':'core d_ctl4 freeze g/lease and hold until accept_ready; acc_done only afterprotectedresultguard','RESULT':'core S_ACC consumes acc_a for Engram rst_slot; resultmuststaystable through consumer handshake; receipt only local result taken, notKVrollback/free','source_adapter':'pulseTOKX/AMAX/ACCEPT become held requests and core S_ISSUE stalls untilmatching accepted handshake; two origin records charged, actual implementation uninstalled','core_input_rank_SM_context':'one concrete core instance is namespace, no multi-client/context sharing assumed','input_clock_conversion':'single serviceclock kernel only; if actual producer clocks differ, priced CDC queue is mandatory and absenthere','drain_receipts':['allproducers/stamp pipelines empty','allresult consumers done','forward copies drained','return copies drained','reverse copies drained','reset endpoints fenced'], 'runtime_reset':'coldrst_n requiresallcopiesfence; runtime rearm idle/stopped only afterpositive matched receipts, acceptedfaultdebtcannoterase'})
 return model

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--verify',action='store_true');ap.add_argument('--out',type=Path);a=ap.parse_args();b=(json.dumps(model(),indent=2,sort_keys=True)+'\n').encode();p=a.out or OUT/'model.json'
 if a.verify:
  assert p.read_bytes()==b;print('PASS byte-exact leaf model/source pins; no physical/whole-MTP admission')
 else:p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b);print(p)
if __name__=='__main__':main()
