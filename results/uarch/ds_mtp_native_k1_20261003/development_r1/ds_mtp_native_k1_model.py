"""Independent native command/origin adapter plus conditional exact runtime-k1.

Analytical/behavioral model only. Full original K512 remains the literal RTL
oracle and indexed-path block; no RTL, physical clock or MTP rate is inferred.
"""
import argparse,collections,hashlib,json,math
from pathlib import Path
import ds_mtp_accept_leaf_model as L
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results/uarch/ds_mtp_native_k1_20261003'
SOURCES=['rtl/hdc/v41/ot_hdc_select.sv','rtl/hdc/v41x/ot_hdc_v41x_xu_adapt.sv',
 'rtl/hdc/v41x/ot_hdc_v41x_me_adapt.sv','rtl/w17_runtime/hdc/v41x/ot_hdc_core_v41x.sv',
 'rtl/w17_runtime/chip/ot_chip_v41x_tile.sv','rtl/v41die/ot_v41_rom_adapt.sv',
 'tools/hdc_program_v41.py','rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv',
 'rtl/experimental/ds_mtp_accept_20261003/ot_hdc_mtp_accept_guarded.sv',
 'rtl/experimental/ds_mtp_accept_20261003/ot_hdc_mtp_source_holders.sv',
 'tools/ds_mtp_accept_leaf_model.py',
 'results/uarch/ds_mtp_accept_leaf_20261003/inputs/results/uarch/w2_pc_exact_completion_20261003/inputs/cell_prices.json']
JOB=[('lease',25),('slot',3),('engine',2),('lane',3),('cmdpc',32),('token',21),('phase',3),('seen',1),('launch_receipt',1),('n',21),('k',12),('bf16',1),('op',2),('amax',1),('m',3),('wsrc',1)]
QUERY=[('lease',25),('slot',3),('lane',3),('ctlpc',32),('valid',1)]
COHORT=[('lease',25),('g',3),('used',16),('stop',1),('fault',1),('fenced',1)]
META=[('src',30),('dst',30),('n',21),('issued',21),('captured',21),('consumed',21),('phase',3),('stop',1),('fault',1),('head',1),('tail',1)]
IDLE,OFFER,ARM,ACTIVE,TERMINAL,FINISH,DONE=range(7)

def width(fields):return sum(b for k,b in fields)
def pack(fields,d):
 raw=shift=0
 for name,b in fields:
  v=d.get(name,0)
  if type(v)!=int or not 0<=v<1<<b:raise ValueError('field '+name)
  raw|=v<<shift;shift+=b
 return [L.encode64((raw>>(64*i))&((1<<64)-1)) for i in range(math.ceil(shift/64))]
def unpack(fields,words):
 raw=0;bits=width(fields)
 if len(words)!=math.ceil(bits/64):raise ValueError('word count')
 for i,c in enumerate(words):
  d,ce,ue=L.decode64(c)
  if ue:raise ValueError('uncorrectable record')
  raw|=d<<(64*i)
 if raw>>bits:raise ValueError('coded padding')
 out={};shift=0
 for name,b in fields:out[name]=(raw>>shift)&((1<<b)-1);shift+=b
 return out

def fpkey(bits):
 if bits&0x7f800000==0x7f800000 and bits&0x7fffff:raise ValueError('NaN outside pinned source contract')
 if bits&0x7fffffff==0:return 0x80000000
 return (~bits&0xffffffff) if bits>>31 else bits|0x80000000

def full512_reference(scores,k):
 """Functional full512 insertion cells (not reducedK oracle, not RTL evidence).

 Rank population is bounded to512 like source; only runtime-k cells pass the
 original threshold into ORDER1 emission. Matches source valid/key/~idx compare.
 """
 if not 0<=k<=512:raise ValueError('k')
 cells=[];seen=set()
 for idx,bits in scores:
  if not 0<=idx<1<<21 or not 0<=bits<1<<32 or idx in seen:raise ValueError('source unique full21 index')
  seen.add(idx);entry=(fpkey(bits),-idx,idx)
  pos=0
  while pos<len(cells) and cells[pos]>entry:pos+=1
  cells.insert(pos,entry)
  if len(cells)>512:cells.pop()
 return sorted(x[2] for x in cells[:k])

class K1:
 """Protected max tuple reference. Contiguous native vocab stream only."""
 def __init__(self,n):
  if not 1<=n<=L.VOCAB:raise ValueError('nonzero bounded count')
  self.meta=pack(META,dict(n=n,phase=1));self.winner=L.encode64(0)
  self.out=pack([('idx',21),('last',1),('ninf',1),('valid',1)],{})
 def accept(self,idx,bits):
  m=unpack(META,self.meta);r=L.decode64(self.winner)
  if r[2] or r[0]>>55:raise ValueError('poisoned winner')
  if m['phase']!=1 or idx!=m['consumed'] or idx>=m['n']:raise ValueError('native ordered stream')
  key=fpkey(bits);raw=r[0];valid=raw&1;oldkey=(raw>>1)&0xffffffff;oldidx=(raw>>33)&L.MASK
  if not valid or key>oldkey or (key==oldkey and idx<oldidx):
   self.winner=L.encode64(1|(key<<1)|(idx<<33)|(int(bits==0xff800000)<<54))
  m['issued']=m['captured']=m['consumed']=idx+1
  if m['consumed']==m['n']:m['phase']=2
  self.meta=pack(META,m)
 def publish(self):
  m=unpack(META,self.meta);raw,ce,ue=L.decode64(self.winner)
  if ue or raw>>55 or not raw&1 or m['phase']!=2:raise ValueError('not complete clean winner')
  self.out=pack([('idx',21),('last',1),('ninf',1),('valid',1)],dict(idx=(raw>>33)&L.MASK,last=1,ninf=(raw>>54)&1,valid=1))
  m['phase']=3;self.meta=pack(META,m);return self.output()
 def output(self):
  d=unpack([('idx',21),('last',1),('ninf',1),('valid',1)],self.out)
  return (d['idx'],d['last'],d['ninf']) if d['valid'] else None
 def take(self,ready):
  out=self.output()
  if not ready or out is None:return False
  self.out=pack([('idx',21),('last',1),('ninf',1),('valid',1)],{});return True

class NativeAdapter:
 """9 coded words: two jobs, two CTL queries and one cohort.

 A core issue offer is not backend acceptance. Hold S_GO and native descriptor
 until actual registered ARM launch + holder begin, then matching launch receipt.
 No current descriptor retag at provider terminal or CTL publication.
 """
 def __init__(self,lease,g,*,x_me=1,x_rom=0,cold_fenced=False):
  if not cold_fenced:raise ValueError("truthful cold allcopies fence required")
  pos,gen=lease
  if not 0<=g<8 or not 0<=pos<=L.MASK-g or not 0<=gen<16:raise ValueError('cohort bounds')
  self.c=pack(COHORT,dict(lease=pos|(gen<<21),g=g));self.jobs=[pack(JOB,{}),pack(JOB,{})];self.q=[pack(QUERY,{}),pack(QUERY,{})]
  self.x_me=x_me;self.x_rom=x_rom
 def view(self):
  try:
   c=unpack(COHORT,self.c);j=[unpack(JOB,x)for x in self.jobs];q=[unpack(QUERY,x)for x in self.q]
   if c['fault']:raise ValueError('sticky quarantine')
   for k,r in enumerate(j):
    if r['phase']>DONE or r['token']>=L.VOCAB:raise ValueError('semantic record')
    if r['phase'] and (r['lease']!=c['lease'] or not (1 if k==0 else 0)<=r['slot']<=c['g'] or r['lane']!=0):raise ValueError('owned identity')
    if r['phase']:
     if k==0 and not(1<=r['n']<=L.VOCAB and r['k']==1 and not r['bf16'] and r['op']==0):raise ValueError('changed TOKX qualifier')
     if k==1 and (self.x_rom or r['engine']!=int(bool(self.x_me or self.x_rom)) or not r['amax'] or r['wsrc'] or r['m'] not in (0,1) or not 1<=r['n']<=L.VOCAB):raise ValueError('changed AMAX qualifier')
    if q[k]['valid'] and (r['phase'] not in (TERMINAL,FINISH,DONE) or (q[k]['lease'],q[k]['slot'],q[k]['lane'])!=(r['lease'],r['slot'],r['lane'])):raise ValueError('invalid CTL query')
    if r['phase'] in (FINISH,DONE) and not q[k]['valid']:raise ValueError('lost CTL ownership')
   return c,j,q
  except ValueError:
   # Retain every job/query word; coded global failure blocks normal grants.
   try:
    c=unpack(COHORT,self.c);c['fault']=1;self.c=pack(COHORT,c)
   except ValueError:pass
   raise
 def fail(self):
  c=unpack(COHORT,self.c);c['fault']=1;self.c=pack(COHORT,c);return False
 def offer(self,kind,*,slot,cmdpc,engine=0,lane=0,n=L.VOCAB,k=1,bf16=0,op=0,amax=0,m=1,wsrc=0):
  c,j,q=self.view()
  if c['stop'] or j[kind]['phase']!=IDLE:return False
  if not (1 if kind==0 else 0)<=slot<=c['g'] or lane!=0 or c['used']>>(8*kind+slot)&1:return self.fail()
  expected=(1 if self.x_me or self.x_rom else 0)
  if kind==0 and not(n>0 and n<=L.VOCAB and k==1 and not bf16 and op==0):return self.fail()
  if kind==1 and (self.x_rom or engine!=expected or not amax or wsrc or m not in (0,1) or not 1<=n<=L.VOCAB):return self.fail()
  r=dict(lease=c['lease'],slot=slot,cmdpc=cmdpc,engine=engine,lane=lane,phase=OFFER,n=n,k=k,bf16=bf16,op=op,amax=amax,m=m,wsrc=wsrc)
  self.jobs[kind]=pack(JOB,r);c['used']|=1<<(8*kind+slot);self.c=pack(COHORT,c);return True
 def arm(self,kind):
  c,j,q=self.view();r=j[kind]
  if r['phase']!=OFFER:return False
  r['phase']=ARM;self.jobs[kind]=pack(JOB,r);return True
 def launch(self,kind,*,native_ready,holder_begin_ready,discovery_bad=False):
  c,j,q=self.view();r=j[kind]
  if discovery_bad:self.fail();return None
  if r['phase']!=ARM or not native_ready or not holder_begin_ready:return None
  r['phase']=ACTIVE;r['launch_receipt']=1;self.jobs[kind]=pack(JOB,r)
  return r['lease'],r['slot'],0,0 # original begin52 body, finish0
 def launch_take(self,kind,*,lease,cmdpc,ready):
  c,j,q=self.view();r=j[kind]
  if not ready or not r['launch_receipt']:return False
  if lease!=r['lease'] or cmdpc!=r['cmdpc']:return self.fail()
  r['launch_receipt']=0;self.jobs[kind]=pack(JOB,r);return True
 def observe(self,kind,*,idle,token=0,valid=True,engine=None,source_fault=False,source_reset=False,intermediate_ov=False):
  c,j,q=self.view();r=j[kind]
  if source_fault or source_reset:return self.fail()
  if r['phase']!=ACTIVE:return False
  if kind==1 and engine!=r['engine']:return self.fail()
  if not idle:r['seen']=1;self.jobs[kind]=pack(JOB,r);return False
  if not r['seen'] or r['launch_receipt']:return False
  if not valid or not 0<=token<L.VOCAB:return self.fail()
  r['token']=token;r['phase']=TERMINAL;self.jobs[kind]=pack(JOB,r);return True
 def ctl_offer(self,kind,*,lease,slot,lane,ctlpc):
  c,j,q=self.view();r=j[kind]
  if r['phase']!=TERMINAL or q[kind]['valid']:return False
  self.q[kind]=pack(QUERY,dict(lease=lease,slot=slot,lane=lane,ctlpc=ctlpc,valid=1));return True
 def ctl_check(self,kind):
  c,j,q=self.view();r=j[kind];req=q[kind]
  if not req['valid'] or r['phase']!=TERMINAL:return False
  if (req['lease'],req['slot'],req['lane'])!=(r['lease'],r['slot'],r['lane']):return self.fail()
  r['phase']=FINISH;self.jobs[kind]=pack(JOB,r);return True
 def output(self,kind):
  c,j,q=self.view();r=j[kind]
  return (r['lease'],r['slot'],r['token'],1) if r['phase']==FINISH else None
 def finish_take(self,kind,*,ready):
  c,j,q=self.view();r=j[kind]
  if not ready or r['phase']!=FINISH:return False
  r['phase']=DONE;self.jobs[kind]=pack(JOB,r);return True
 def ctl_take(self,kind,*,lease,ctlpc,ready):
  c,j,q=self.view();r=j[kind];req=q[kind]
  if not ready or r['phase']!=DONE:return False
  if lease!=req['lease'] or ctlpc!=req['ctlpc']:return self.fail()
  self.jobs[kind]=pack(JOB,{});self.q[kind]=pack(QUERY,{});return True
 def fence(self,*,lease,receipts,providers_idle,holders_empty,reverse_CDC_empty):
  c,j,q=self.view()
  if lease!=c['lease'] or receipts!=63 or not providers_idle or not holders_empty or not reverse_CDC_empty or any(r['phase'] or r['launch_receipt'] for r in j) or any(r['valid'] for r in q):return self.fail()
  c['used']=0;c['stop']=1;c['fenced']=1;self.c=pack(COHORT,c);return True
 def rearm(self,lease,g,*,accepted_leaf_start):
  c,j,q=self.view();pos,gen=lease
  if not accepted_leaf_start or not c['fenced'] or not c['stop'] or c['used'] or any(r['phase'] for r in j) or any(r['valid'] for r in q):return self.fail()
  if not 0<=g<8 or not 0<=pos<=L.MASK-g or gen!=(((c['lease']>>21)+1)&15):return self.fail()
  self.c=pack(COHORT,dict(lease=pos|(gen<<21),g=g));return True

def tree(n,f):
 out=[]
 while n>1:n=math.ceil(n/f);out.append(n);f=8
 return out

def price(words,raw,*,native):
 facts=json.loads((ROOT/SOURCES[-1]).read_text())['facts'];bits=words*72;sections={}
 g=L.Gates()
 for _ in range(words):g.codec()
 g.OR(words*64-raw);g.OR(words-1);sections['current_codecs_padding_and_joint_guard']=g.dict()
 g=L.Gates();g.mux(raw,8)
 if native:
  for _ in range(8):g.eq(25);g.eq(3)
  for _ in range(4):g.eq(32);g.lt_const(21,L.VOCAB)
  g.mux(24,4);g.mux(1,4);g.mux(52,2);g.const_eq(6,63);g.const_eq(12,1)
  g.lt_const(21,L.VOCAB+1);g.eq(2);g.eq(3);g.AND(96);g.OR(96)
 else:
  g.nand(12*53);g.inv(8*53);g.mux(55,2);g.inv(21)
  g.const_eq(31,0);g.const_eq(8,255);g.OR(31);g.mux(32,2)
  for _ in range(4):g.add(21);g.eq(21)
  g.add(30);g.lt_const(30,1<<30);g.mux(56,2);g.eq(2);g.AND(64);g.OR(64)
 sections['source_comparison_or_native_identity_route_and_controls']=g.dict()
 reset=tree(bits,7);clock=tree(bits,8)
 sections['storage_hold_restore_clock_reset_and_fanout_minimum']={
 'DFFASRHQNx1_ASAP7_75t_R':bits,'INVx1_ASAP7_75t_R':2*bits,'NAND2x1_ASAP7_75t_R':3*bits,
 'BUFx4_ASAP7_75t_R':2*bits+sum(reset)+sum(clock)+4*L.buffers(bits)}
 total=collections.Counter()
 for s in sections.values():total.update(s)
 body=sum(n*facts[name]['SS']['area_um2'] for name,n in total.items())
 return dict(raw_bits=raw,codewords=words,protected_bits=bits,cell_counts_by_section=sections,cell_counts_total=dict(sorted(total.items())),gross_body_um2=body,gross50pct_mm2=body/.5/1e6,clock_minimum=clock,reset_minimum=reset,wire_sites_and_net_debit=None)

def model():
 pins=json.loads((OUT/'input_manifest.json').read_text())
 for p in pins:
  assert hashlib.sha256((ROOT/p['path']).read_bytes()).hexdigest()==p['sha256'],p['path']
  assert hashlib.sha256((OUT/p['archive']).read_bytes()).hexdigest()==p['sha256']
 core=(ROOT/SOURCES[3]).read_text();rom=(ROOT/SOURCES[5]).read_text();xu=(ROOT/SOURCES[1]).read_text();prog=(ROOT/SOURCES[6]).read_text()
 assert '((X_ME != 0 || X_ROM != 0)' in core and '(X_ME != 0) ? 1 : 0' in core
 assert "m_round && !m_amax && !m_mmode" in rom and '.IW(16)' in xu
 assert 'not f.get("me_amax", 0)' in prog
 native_raw=2*width(JOB)+2*width(QUERY)+width(COHORT);native_words=2*math.ceil(width(JOB)/64)+2+1
 kernel_raw=width(META)+2*56+55+24;kernel_words=math.ceil(width(META)/64)+2+1+1
 native=price(native_words,native_raw,native=True);k1=price(kernel_words,kernel_raw,native=False)
 old=json.loads((OUT/'full_scalar_594fee_model.json').read_text());saved=1537-2
 return dict(schema='DS_MTP_NATIVE_ADAPTER_AND_EXACT_K1_R1',base='f1a9eb944dc01992012eab62bca78ae194ecf5eb',default_enable=False,
 source_pins=pins,native_adapter=dict(selected_NSLOT=8,NW=21,MP=1,PC_wire_bits=32,source_PC_default14_reduced_peer16='32bit zeroextension priced; actual selected program bounds must be checked',records=dict(job_fields=JOB,query_fields=QUERY,cohort_fields=COHORT),cost=native,
 acceptance='source S_ISSUE registers oldgo; adapter captures offer, ARM oneedge later; actual next accepted backendgo requires current native ready+holder beginready and current joint coded guard. Hold core S_GO and descriptors until matching launchreceipt; no launchintent called native acceptance',
 terminal='retain accepted engine2/lane3/lease25/slot3/cmdPC32; observe active then idle+valid final21 token; XU full21 and ME actual selected engine required; ignore intermediate ov',
 publication='matching actual CTL query lease/slot/lane with current ctlPC32 captured, checked, then original finish52 held through holderready; core CTL PCadvance waits matching receipt. No expectedconsumerPC fabricated; actual whole-program serialized pair audit still required',
 source_ports=dict(issue_body_bits=25+3+2+3+32+41,issue_valid_ready_signals=2,ME_return4engines_bits=4*24,ME_readies_bits=4,ME_go_demux_bits=4,XU_return_bits=21+1+1+1,holder_begin_finish_cuts=[52,52],launch_receipt_body_bits=25+32,launch_receipt_valid_ready=2,CTL_query_body_bits=63,CTL_query_valid_ready=2,CTL_receipt_body_bits=25+32,CTL_receipt_valid_ready=2,source_fault_reset_stop_bits=6,lease_g_cut_bits=25+3+2,fence_cut_bits=25+6+3+2,legal_channel_tracks=None),
 calendar=dict(issue_offer_to_actual_native_accept_edges_min=2,actual_accept_to_core_launchreceipt_take_edges_min=1,terminal_capture_to_holder_finish_edges_min=3,terminal_capture_to_core_CTL_release_edges_min=4,extra_vs_legacy_upper_edges_per_native_child=6,finite_child_slots=2,held_wait_bound=None,prospective_clock_GHz=.9,source_clk_same_as_core=True,installed_split_serial_clock=False,codec_feedback_loaded_SS_FF=False),
 model_state_ports_calendar_complete=True,component_model_verdict='PASS_CONDITIONAL_SAMECLOCK_PORT_STATE_CALENDAR; connected-source and physical gates fail separately',component_functional_preparation_eligible='conditional parent enrollment at specified sameclock interface; independent of K512 physical slot, not build authorization',connected_source_G0=False),
 k1=dict(conditional_selection='ONLY active FP32 OP_SEL static count>0<=vocab runtimek1, full21 native walker; BF16/dynamic/TOPK512/routerk6 use preserved original K512 paths',exactness='same FP32 order key, -0=+0, lower index ties, +/-Inf retained; NaN outside pinned contract, no arithmetic or rounding change',
 records=dict(meta_fields=META,VM_reservation_records=2,VM_reservation_raw_each=56,winner_raw=55,held_index_output_raw=24),cost=k1,
 ports=dict(MACs_per_cycle=0,VM_read_bytes_per_edge=4,VM_write_bytes_per_edge=4,VM_request_signals=31,VM_return_signals=32,VM_write_signals=63,score_payload_bits=32+21+1,score_valid_ready=2,index_payload_bits=21+1+1,index_valid_ready=2,source_VM_return_has_ready=False,reservations_before_issue=2,VM_fixed_latency_enrolled=False),
 calendar=dict(prospective_input_II=1,after_last_input_to_held_output_edges=1,after_last_to_output_handshake_min_edges=2,unbounded_held_waits=True,loaded_decode_compare_encode_SS_FF=False,post_first_emission_tail_removed=511,no_threshold_wave_or_sort=True),
 source_K512_unchanged=True,literal_required_RTL_oracle='unchanged rtl/hdc/v41/ot_hdc_select.sv K512 VW32 IW21 ORDER1 runtimek1, allfull21/highindex/held/fault cases; NEVER K1oracle',literal_RTL_gate_run=False),
 comparison=dict(reference='594fee full source-compatible private protected scalar allowance, NOT built/adopted and NOT an actual net area debit',reference_gross50pct_mm2=old['cost']['gross50pct_mm2'],new_joint_gross50pct_mm2=native['gross50pct_mm2']+k1['gross50pct_mm2'],no_blind_add_to_594=True,actual_indexed_K512_remaining_price_and_protection_unknown=True,
 old_after_last_through_tail_edges=1537,new_after_last_through_first_handshake_edges=2,conditional_saved_edges_per_TOKX=saved,source_vocab=129280,
 same_adapter_same_II_segment_rate_gain_pct=100*saved/(129280+2),
 vs_original_with_new_adapter='net saved edges =1535*nTOKX -6*nAllNativeOrigins - extra loaded-stage/VM/CDC/wait edges, then /0.9 ns prospective only',
 one_percent_per_user_rate_gate='PASS only if actual old whole-iteration time_ns <=101*net_saved_ns and net_saved_ns>0. Exact actual producer counts and whole calendar must be supplied; no current whole-token PASS',whole_token_saving_qualified=False,scalar_physical_slot_not_required_for_native_component_model=True),
 blockers=dict(ROM_AMAX='X_ROM branch engine1 am_idx/am_any zero; ot_v41_rom_adapt m_ok explicitly rejects m_amax, rom_fault_w not e_fault1. Need actual priced/gated ROM head-result provider; fixing EAM alone insufficient',EAM_mismatch='me_eng uses X_ME||X_ROM, EAM uses only X_ME; bind retained actual engine and real return-valid',XU21='current sel_first16 cannot produce full21; requires selected exactk1 or widened/protected source endpoint',upstream_descriptor_protection='core descriptors held until actual acceptance; their full protection/source clock/reset still unenrolled',actual_program_pairs='Builder serial=True protects head/CTL pairs and excludes AMAX batching; actual installed whole program/cmdPC trace not supplied',clock_and_home='Arch/Maxwell loaded stage/sourceclock/home/channel decisions pending',reset_wrap='positive provider+holder+reverseCDC drain required; localempty/mask cannot prove externaloldcopies'),
 admission=dict(no_RTL_or_P_and_R=True,model_only=True,whole_MTP=False,rate_or_tau_adopted=False,physical_G0=False,standalone_native_cost_does_not_depend_on_K512_capacity=True))

def main():
 p=argparse.ArgumentParser();p.add_argument('--verify',action='store_true');p.add_argument('--out',type=Path);a=p.parse_args()
 data=(json.dumps(model(),indent=2,sort_keys=True)+'\n').encode();out=a.out or OUT/'model.json'
 if a.verify:assert out.read_bytes()==data;print('PASS source-bound native adapter and conditional exactk1 byteexact model')
 else:out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(data);print(out)
if __name__=='__main__':main()
