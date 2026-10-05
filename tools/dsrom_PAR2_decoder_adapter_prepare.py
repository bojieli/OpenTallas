#!/usr/bin/env python3
"""Opt-in bit-order and finite terminal model, not engine RTL/provider evidence.
Four raw decode/gather grants follow Maxwell13cc; original images untouched.
"""
import collections,dataclasses,gzip,hashlib,importlib.util,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results/uarch/dsrom_PAR2_decoder_adapter_prepare_20261002'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ecc_source():
 s=importlib.util.spec_from_file_location('retained_ecc',OUT/'inputs/ecc.py');e=importlib.util.module_from_spec(s);s.loader.exec_module(e);return e

def split_protected_main(payload,*,enabled=False):
 if not enabled:raise ValueError('opt-in protected producer required; legacy raw images excluded')
 if not 0<=payload<1<<272:raise ValueError('272bit payload')
 cw=ecc_source().encode(payload,272)
 return cw&((1<<274)-1),(cw>>274)&255

def join_main(main274,side8):
 if not 0<=main274<1<<274 or not 0<=side8<256:raise ValueError('physical widths')
 return main274|(side8<<274)

def protected_sidecar_word(fields):
 """Proposed copy producer: 32 side8 fields in exact linear-bit order.
 Only whole-word protected source can enter mirror; no activation/golden injection.
 """
 if len(fields)!=32 or any(not 0<=b<256 for b in fields):raise ValueError('32source parity bytes')
 raw=sum(b<<(8*i) for i,b in enumerate(fields));return ecc_source().encode(raw,256)

@dataclasses.dataclass(frozen=True)
class Lease:
 stage:int;rank:int;shard:int;phase:int;opseq:int;era:int
 def __post_init__(self):
  if any(not 0<=v<1<<w for v,w in zip(dataclasses.astuple(self),(6,2,1,10,13,1))):raise ValueError('source lease identity width')

@dataclasses.dataclass(frozen=True)
class Read:
 lease:Lease;pidx:int;mb:int;pp:int;row:int;slot16:int
 def __post_init__(self):
  if not 0<=self.pidx<103 or self.mb not in (0,1) or self.pp not in (0,1) or not 0<=self.row<4096 or not 0<=self.slot16<16:raise ValueError('canonical physical/field coordinate')
 @property
 def leaf(self):return self.pidx,self.mb,self.pp
 @property
 def word(self):return self.leaf,self.row

class TerminalModel:
 """Finite accepted-read/capture prototype; no cycle/RTL service guarantee.
 One active owner lease,1read debt perleaf,4shared decode grants peredge.
 Raw terminal is distinct from main terminal, consumer ACK and drained owner.
 """
 def __init__(self,lease):
  self.lease=lease;self.reads={};self.captures={};self.raw_visible={};self.main_visible={};self.acks=set();self.fault=False;self.cancelled=False;self.completed_words=set();self.pending_reads=set()
 def accept(self,ticket,read):
  if self.cancelled or self.fault or read.lease!=self.lease:raise ValueError('lease not accepting')
  if ticket in self.reads or len(self.reads)>=128:raise ValueError('duplicate/finite128pair seats')
  # Exact same leaf/row may coalesce; different rows cannot share one debt.
  if any(r.leaf==read.leaf and r.row!=read.row and t not in self.acks for t,r in self.reads.items()):raise ValueError('single outstanding row perleaf')
  if read.word in self.completed_words:raise ValueError('late coalescing requires explicit retained raw-cache contract')
  self.reads[ticket]=read;self.pending_reads.add(read.word)
 def capture(self,read,raw274):
  if read.lease!=self.lease or self.cancelled:raise ValueError('stale/cancelled capture must quarantine')
  if not 0<=raw274<1<<274:raise ValueError('raw274')
  if not any(r.word==read.word for r in self.reads.values()):raise ValueError('capture without accepted read')
  if read.word not in self.pending_reads or read.word in self.captures or read.word in self.completed_words:raise ValueError('duplicate capture')
  if len(self.captures)>=4:raise ValueError('four phase-selected shared capture seats')
  self.pending_reads.remove(read.word);self.captures[read.word]=raw274
 def raw_terminals(self,words):
  if self.cancelled or self.fault:raise ValueError('cancelled/poisoned response must drain, cannot publish')
  if len(words)>4 or len(set(words))!=len(words):raise ValueError('4shared grants peredge')
  for word in words:
   if word not in self.captures:raise ValueError('terminal before accepted capture')
   raw,status=ecc_source().decode(self.captures.pop(word)&((1<<266)-1),256);self.completed_words.add(word)
   if status=='uncorrectable':self.fault=True;continue
   if self.fault:continue
   for ticket,r in self.reads.items():
    if r.word==word:self.raw_visible[ticket]=(raw>>(16*r.slot16))&65535
 def main_terminal(self,ticket,mb,main274):
  if self.fault or self.cancelled or ticket not in self.raw_visible or mb not in (0,1):raise ValueError('no matching good raw terminal')
  key=ticket,mb
  if key in self.main_visible:raise ValueError('duplicate main terminal')
  side=(self.raw_visible[ticket]>>(8*mb))&255;payload,status=ecc_source().decode(join_main(main274,side),272)
  if status=='uncorrectable':self.fault=True;return
  self.main_visible[key]=payload
 def consumer_ack(self,ticket):
  if self.fault or self.cancelled or not all((ticket,mb) in self.main_visible for mb in (0,1)):raise ValueError('ACK before both main terminals')
  if ticket in self.acks:raise ValueError('duplicateACK')
  self.acks.add(ticket)
 def rearm(self,lease):
  if not self.drained or lease==self.lease:raise ValueError('lease rearm requires all physical and consumer debts drained and newidentity')
  self.__init__(lease)
 def cancel(self):self.cancelled=True
 def retire_cancelled(self,ticket):
  if not self.cancelled and not self.fault:raise ValueError('normal operation requires consumer ACK')
  if ticket not in self.reads:raise ValueError('unknown canceled debt')
  r=self.reads[ticket]
  if r.word in self.captures or r.word in self.pending_reads:raise ValueError('physical response debt still present')
  self.acks.add(ticket)
 def quarantine_return(self,read):
  if not self.cancelled and not self.fault:raise ValueError('normal read requires capture+terminal')
  if read.lease!=self.lease or read.word not in self.pending_reads:raise ValueError('stale or duplicate quarantined return')
  self.pending_reads.remove(read.word)
 def drain_capture(self,word):
  if not self.cancelled and not self.fault:raise ValueError('not canceled drain')
  if word not in self.captures:raise ValueError('unknown capture')
  del self.captures[word]
 @property
 def drained(self):return len(self.acks)==len(self.reads) and not self.captures and not self.pending_reads

def build():
 receipt=json.loads((OUT/'input_receipt.json').read_text())
 for n,r in receipt['inputs'].items():assert sha(OUT/'inputs'/n)==r['sha256']
 addr=(OUT/'inputs/native_address_source.py').read_text();assert "[272,274] if fmt=='fp4'" in addr
 pack=(OUT/'inputs/legacy_payload_packer.py').read_text();assert 'w |= m.block_word(row, c, b) << (136 * half)' in pack
 finite=json.loads((OUT/'inputs/finite_model.json').read_text());profiles=json.loads(gzip.decompress((OUT/'inputs/demand_profiles.json.gz').read_bytes()))['records'];assert len(profiles)==46080
 worst=max(profiles,key=lambda p:p['prefetch_single_read_port_per_leaf_cycles']);assert worst['unique_raw256_reads']==800 and worst['prefetch_single_read_port_per_leaf_cycles']==400
 maxbanks=max(p['touched_leaf_banks'] for p in profiles);assert maxbanks==4
 # Actual module word-bit interface, source-equivalent elementary operation
 # counts; geometry and timing mapping needed before implementation acceptance.
 identity_bits=6+2+1+10+13+1+7+1+1+12
 capture_bits=4*(266+identity_bits+1);request_bits=128*(identity_bits+4+2)
 return dict(schema='opentallas.dsrom.PAR2.decoder-adapter-prepare.v1',candidate=finite['candidate_id'],source_main_pin=receipt['source_main_pin'],input_receipt_sha256=sha(OUT/'input_receipt.json'),generator_sha256=sha(Path(__file__)),
  producer_contract=dict(opt_in_default=False,status='PROPOSED_SOURCE_ORDERED_PROTECTED_PRODUCER_NOT_EXISTING_IMAGE_ABI',unchanged_payload_range=[0,272],main274=dict(data=[0,272],inline_check0_1=[272,274]),side8=dict(check2_8=[0,7],overall_parity_bit=7),decoder282=dict(data=[0,272],check0_8=[272,281],overall=281,assembly='cw282={side8[7:0],main274[273:0]}'),sidecar_protection=dict(data256='32 source side8 fields packed increasinglinearbit; bytei at8*i',check9=[256,265],overall=265,physical274_reserved8=[266,274],decoder266='raw274[265:0]'),current_payload_packer_emits_no_protected_checks=True,actual_allocation_ROM_init_producer_missing=True,immutable_mirror_must_copy_full256plus10_source_word=True,no_payload_or_scale_reencoding=True),
  finite_context=dict(source='Maxwell13cc full46509 allocation profile,46080FP4 records',phase_owner_leases=1,shared_raw_decoder_replicas=4,raw_capture_seats=4,raw_capture_state_bits=capture_bits,request_seats=128,request_identity_bits=request_bits,read_debt_per_selected_leaf=1,source_available_leaves=412,max_phase_selected_leaf_banks=maxbanks,max_phase_prefetch_raw_reads=800,max_phase_read_rounds_per_single_port_leaf=400,max_phase_prefetch_data_bits=max(p['prefetch_buffer_required_data_bits'] for p in profiles),raw_decoder_input_bits_per_cycle=4*266,corrected_gather_output_bits_per_cycle=4*256,consumer_parity_bits_per_cycle_bound=2048,raw266_412to4_mux2_nodes=4*266*411,source_epoch_era_opseq_and_phase_fields=dataclasses.asdict(Lease(0,0,1,0,0,0)),read_capture_prototype_not_executed_RTL=True,allleaf_singlecycle_or_prefetch_overlap_guarantee=False,accepted_event_order=['owner/config/descriptor ready','accepted canonical+local read identity','matched macro capture','protected256+10 raw good/corrected terminal','exactmatching8bit field paired to mainword','272+10 main terminal','arithmetic consumer acceptance','ordered consumerACK','all physical capture/read/main debts drained before lease/epochreuse']),
  physical_clock=dict(target_Hz=1200000000,SS_setup_uncertainty_ps=60,FF_hold_uncertainty_ps=25,existing_macro_SS_capture_residual_before_setup_wire_ps=29.37063310661025,mandatory_cone='macroQ ->412:4 selector+wire ->capture; captureQ ->K256 SECDED ->parity gather; mainQ+parity ->K272 SECDED ->arithmetic accept',rejection='No1cycle grant/read credit until actual select/load/route/capture setup+relativeclock insertion fits residual andFFhold. Keep rawcreditsuntilrealterminal. Sourcehold/multicycle requires actualscheduler proof.',common_controller_plus2cycles='Retain priorpriced diagnostic separately; no automatic overlap/decoder credit.',physical_context_needs={'main_read_capture': 'Actual unchanged element PP/MB/main274 capture pin source and eventedge; ownernewfault/ready connection missing.','raw_read_capture':'No source-owned selectedbank/capturewrapper currently connects K256 decoder; this is modelprep only.','decoder_order':'Exactconcat above is proposedproducerABI, requiresNash freeze/realencodedwords.','placement':'4shareddecoders+412:4mux +128queues with actual pins/OBS/PG/vias must be placed within wholecandidate context.'}),
  composed_latency_contract=dict(calendar_owner='Maxwell, samePAR2',source_deadlines_not_bound=True,read_service_lower_bound='max(maxuniquerows_perleaf,ceil(uniqueRawReads/4))=400 rounds for worstphase before latency/serialization; not tokencycles.',no_default_service_latencies=True,required_calibrated_inputs=['accepted descriptor readiness','mainword sourcecaptureedges','rawreadII','actualcapturelatency','rawdecoderlatency','gatherdelivery','main decoderterminal latency','reversecredit','original dependent deadlines'],exposed_criticalpath='Dependent consumer can issue only after matching mainterminal; stalls propagate to source ordered descendants. Fullphaseprefetch need204800bits at worst, no freeworkspace/reuse/overlap.'),
  historical_412local_decoder_model='Four-shared prototype follows13cc storage proposal only, NOT selected physical topology. Maxwell0e123 r5 now carries412 leaf-local raw +256 main decoders; retained f934 geometry and allowances stay charged. Bit-order and finite debt tests remain reusable; four-seat service is not an admission or area credit.',no_engine_RTL_compile_PR_jobs=0)

def main():
 out=OUT/'model.json';raw=(json.dumps(build(),indent=2,sort_keys=True)+'\n').encode()
 if out.exists() and out.read_bytes()!=raw:raise ValueError('immutable model changed')
 out.write_bytes(raw);print(hashlib.sha256(raw).hexdigest())
if __name__=='__main__':main()
