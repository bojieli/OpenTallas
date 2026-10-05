#!/usr/bin/env python3
"""Source-affine field publication and full native VM component join.
No engine RTL, payload reader, launcher or mutable peer imports.
"""
import argparse,hashlib,importlib.util,json,math,re
from dataclasses import dataclass
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/uarch/dsrom_field_native_VM_join_20261003'
CTX_WIDTHS=(6,2,9,10,32,32,32,32,14)

@dataclass(frozen=True)
class SealedPublication:
 ctx:tuple
 era:int
 base:int
 rows:int
 writes:tuple

def provider():
 p=OUT/'inputs/native_calendar.py';spec=importlib.util.spec_from_file_location('frozen_native_VM',p)
 m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 m.BASE=OUT/'inputs/native_provider';m.inputs();return m

def identity(ctx,era):
 if len(ctx)!=9 or any(type(v)is not int or not 0<=v<2**w for v,w in zip(ctx,CTX_WIDTHS)):raise ValueError('full169 context')
 if ctx[0]>=58 or ctx[2]>=384 or type(era)is not int or not 0<=era<2**32:raise ValueError('S58/EID/resetera bounds')
 return tuple(ctx),era

def guard_cost():
 import dsrom_I66_capture_cells as C
 facts,_=C.facts();bits=253+6*593
 # Conservative explicit resettable association floor; no existing row tags,
 # mask state, header RAM or phase-owner FF credited as contained.
 # 236 compare bits:full169+era32+row16+expandedaddress19.
 compare_bits=236
 gates={C.ASR:bits,C.INV:bits+compare_bits+compare_bits-1,
  C.NAND:3*bits+4*compare_bits+compare_bits-1,C.BUF:5*bits,
  'TIEHIx1_ASAP7_75t_R':bits}
 leaves=(bits+3)//4;n=leaves;clock=leaves
 while n>1:n=(n+7)//8;clock+=n
 gates[C.BUF]+=2*clock # positiveCLK andRESET floor, no spatial reach assertion
 body=sum(n*(.04374 if m=='TIEHIx1_ASAP7_75t_R' else facts[m]['SS']['area_um2']) for m,n in gates.items())
 return {'bits':bits,'masters':gates,'body_um2_floor':body,'reservation_mm2_at50percent_floor':body*2/1e6,
  'clock_and_reset_BUF_floor_each':clock,'buffer_typed_feedback2_forward3':True,
  'row_increment_formatter_adder_hold_select_spatial_relays_and_decode_logic_not_in_floor':True,
  'guard_pipeline_cycles':None,'sameedge_guard_not_assumed':True,'existing_containment_credit':0}

def data_CDC_cost():
 import dsrom_I66_capture_cells as C
 facts,_=C.facts();bits=16*69
 # Prior238-bit mailboxes were CONTROL only. One forwarddata mailbox now
 # appends the complete raw69 carrier, rather than relying on unstable data
 # beside a synchronized control. Reverse credits remain238 bits.
 cells={C.HQ:bits,C.INV:bits,C.NAND:3*bits,C.BUF:5*bits}
 leaves=(bits+3)//4;n=leaves;clock=leaves
 while n>1:n=(n+7)//8;clock+=n
 cells[C.BUF]+=clock
 body=sum(facts[m]['SS']['area_um2']*count for m,count in cells.items())
 return {'forward_data_entries':16,'forward_full_payload_bits':307,'reverse_control_payload_bits':238,
  'new_raw_data_bits':bits,'added_masters':cells,'body_um2_floor':body,'reservation_mm2_at50percent_floor':body*2/1e6,
  'clock_BUF_floor':clock,'data_stability':'Full307 held FIFO entry until matched receiver capture; Gray pointers synchronized; no bitwise bus sync or control-only data assumption.',
  'source_issue':'Reserve dataFIFO/native frame seat before scalar read. Refused sink stops scalar issue, never native rawfield root capture.',
  'positive_phase_crossing_screen_stream_edges':7,'actual_CDC_reset_relation_and_registered_timing':False}

def packet_ACK_native_bound():
 # Conservative successful-service screen for one256-flit packet. Native
 #593-seat frames split762 rows; do not borrow read-response seats. Held CRC
 #verification precedes native capture/publish. Both clocks use rational3:4.
 rows=762;frames=(rows+592)//593;native_serial=2*rows+3*frames
 native_stream=math.ceil(native_serial*4/3)
 bound=1337+256*11+native_stream+7+1+1337+1
 return {'packet_rows':rows,'packet_flits':256,'native_frames':frames,
  'native_publication_serial_edges':native_serial,'native_publication_stream_edges':native_stream,
  'successful_ACK_wait_stream_edges_excluding_guard_and_arbitration':bound,
  'timeout1024_PASS':bound<1024,'timeout4096_PASS':bound<4096,'timeout8192_without_guard_PASS':bound<8192,
  'remaining8192_for_guard_arbitration_stream_edges':8192-bound-1,
  'native_frame_guard_tail_and_actual_reply_scheduling_still_required':True,
  '8192_not_adopted_timeout_or_universal_provider_bound':True}

def source_formatter_receipt():
 p=ROOT/'results/uarch/dsrom_field_tree_bridge_20261003/inputs/ot_v41_spine.sv'
 t=re.sub(r'\s+','',p.read_text())
 if "obase+VAW'(r_row[16*kr+:16])+VAW'(r_pos[3*kr+:3])*ops" not in t:raise ValueError('literal source address expression changed')
 return {'path':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'literal_address':'obase + row + pos*ops; AW30 expansion before VM_AW19 bounds', 'formatter_rounding_unchanged':True}

class AffineFrame:
 """Default-off source-qualified write-only field frame, not generic VM scan.

 Reserve actual output extent and suppress/veto competitors before GO. Issue
 scalar reads in increasing row sequence; returned raw records need matched
 owner and row. No caller-supplied unique flag can bypass these predicates.
 """
 def __init__(self,ctx,era,base,rows,positions,extent_lease,writer_drained,other_writers_masked):
  self.ctx,self.era=identity(ctx,era)
  if type(base)is not int or type(rows)is not int or type(positions)is not int or positions!=1 or not 1<=rows<=8192 or not 0<=base<=2**19-rows:raise ValueError('sourceP1 affine output AW19 bounds')
  if not extent_lease or len(writer_drained)!=12 or not all(writer_drained) or not other_writers_masked:raise ValueError('real exclusive extent + native12writer drain/suppression before GO')
  self.base,self.rows=base,rows;self.accepted=[];self.closed=False
 def append(self,ctx,era,row,pos,address,value,raw_source_error=False,competitor=False):
  if self.closed or identity(ctx,era)!=(self.ctx,self.era) or any(type(x)is not int for x in (row,pos,address)) or row!=len(self.accepted) or pos!=0 or address!=self.base+row or row>=self.rows or raw_source_error or competitor or type(value)is not int or not 0<=value<2**32:raise ValueError('owner/affine row/format/fault/competitor guard')
  self.accepted.append((row,address,value))
 def seal(self,reads=(),extra_writes=()):
  if self.closed or len(self.accepted)!=self.rows or reads or extra_writes:raise ValueError('exact source-affine write-only frame, no mixed-source elision')
  self.closed=True
  return SealedPublication(self.ctx,self.era,self.base,self.rows,tuple(self.accepted))

def affine_native_calendar(sealed,epoch):
 """Linear accepted descriptor fill; constant address compare per scalar.

 Only after AffineFrame.seal. Native mask, issue4-bank/entry, visible+2/ACK+3
 unchanged. Raw32 data is transported, not recomputed by a golden callback.
 """
 if not isinstance(sealed,SealedPublication):raise ValueError('sealed affine source certificate required')
 identity(sealed.ctx,sealed.era)
 writes=sealed.writes
 if epoch!=sealed.era or len(writes)!=sealed.rows or not 1<=sealed.rows<=8192 or not 0<=sealed.base<=2**19-sealed.rows or any(w[0]!=i or w[1]!=sealed.base+i or type(w[2])is not int or not 0<=w[2]<2**32 for i,w in enumerate(writes)):raise ValueError('invalid sealed affine certificate')
 v=provider();result=[];cursor=0
 for start in range(0,len(writes),v.WRITE_CAP):
  w=writes[start:start+v.WRITE_CAP]
  if not w or any(w[i][1]+1!=w[i+1][1] for i in range(len(w)-1)):raise ValueError('nonaffine native subframe')
  # Native finite scanner's backend events are reused exactly; only the
  # prior-proved all-unique winner comparison scan is not executed at fill.
  frame=v.calendar({},[],w,epoch)
  fill=len(w);events=[]
  for e in frame['write_events']:
   h=v.word_home(w[e['issue']][1])
   expanded_mask=((1<<32)-1)<<(32*h['lane'])
   events.append({**e,'issue':cursor+fill+e['issue'],
    'macro_visible':cursor+fill+e['macro_visible'],'visible_ack_capture':cursor+fill+e['visible_ack_capture'],
    'expanded512bit_mask_hex':hex(expanded_mask),'four128bit_masks_hex':[hex((expanded_mask>>(128*i))&((1<<128)-1)) for i in range(4)]})
  end=cursor+fill+frame['busy_edges']
  result.append({'row_start':start,'rows':len(w),'accepted_descriptor_fill_edges':fill,
   'winner_compare_edges':0,'reference_scan_removed_edges':frame['winner_compare_edges'],
   'backend_edges':frame['busy_edges'],'frame_end_edge_exclusive':end,'events':events})
  cursor=end # next frame admission on a later edge; no unfinished-frame reuse
 return {'frames':result,'serial_edges':cursor,'serial_ns_at0p9GHz':cursor/.9,'still_conditional_provider_not_measured':True}

class QualifiedReceipt:
 """Full-owner association around native epoch/ID receipts; no live hooks."""
 def __init__(self,frame,ctx,era,batch):
  self.ctx,self.era=identity(ctx,era)
  if type(batch)is not int or not 0<=batch<2**16:raise ValueError('finite batch nonce')
  self.batch=batch;self.frame=frame;self.native=provider().FrameLease(frame,era);self.visible={};self.credit={}
 def receipt(self,ctx,era,batch,direction,rid,edge,postNBA=False):
  if identity(ctx,era)!=(self.ctx,self.era) or batch!=self.batch:raise ValueError('owner/resetera/batch mismatch')
  if direction=='write' and rid not in self.frame['receipts']:raise ValueError('unknown native write identity')
  if direction=='write' and self.frame['receipts'][rid]['kind']=='VISIBLE_WINNER':
   if not postNBA:raise ValueError('requestaccept is not winning postNBA visibility')
  self.native.receipt(direction,rid,era,edge)
  if direction=='write' and self.frame['receipts'][rid]['kind']=='VISIBLE_WINNER':self.visible[rid]=edge
 def source_credit(self,ctx,era,batch,rid,edge):
  if identity(ctx,era)!=(self.ctx,self.era) or batch!=self.batch or rid not in self.visible or rid in self.credit or edge<=self.visible[rid]:raise ValueError('sourcecredit follows samewinner and positive captured delay')
  self.credit[rid]=edge
 def rearm(self,engine_retired,preF):
  winners={rid for rid,r in self.frame['receipts'].items() if r['kind']=='VISIBLE_WINNER'}
  if set(self.credit)!=winners or preF<=max(self.credit.values(),default=-1):raise ValueError('bankrearm only after winningvisible credits BEFORE F')
  self.native.rearm(engine_retired)


def generate():
 receipt=source_formatter_receipt();p=json.loads((OUT/'inputs/provider_model.json').read_text());v=provider()
 ctx=(0,0,0,10,2149580800,0,0,0,66);a=AffineFrame(ctx,0,398720,576,1,True,[True]*12,True)
 for row in range(576):a.append(ctx,0,row,0,398720+row,0x45a00000)
 writes=a.seal();fast=affine_native_calendar(writes,0);reference=v.calendar({},[],writes.writes,0)
 # Raw field capacity4096/shard remains; a full8192 logical output streams
 # through finite593-entry frames, never assumes8192 VM-frame seats.
 full=AffineFrame(ctx,0,0,8192,1,True,[True]*12,True)
 for row in range(8192):full.append(ctx,0,row,0,row,0)
 fullcal=affine_native_calendar(full.seal(),0)
 return {'schema':'DS_FIELD_NATIVE_VM_JOIN_V1','candidate':'DS4096-TP4-S58-PAR2-NP2048',
  'predecessor':'06f7c9590e9a0a7737fdca782f2264fab5f1abba','native_provider_commit':'ce12ffd1472a4cb60110efb6ecc87139554e1e68',
  'source_formatter':receipt,'native_backend':p['selected_backend'],'native_reference_area_floors':p['area'],
  'selected_publication_spec':'Defaultoff P1 field-only affine extent; ordered scalar drain, full169ctx+era32; real12writer drain+extent exclusivity and competitor veto. Generic/mixed reads/writes retain native source read-old+last-winner scanner.',
  'I66_reference_scan':{'fill_edges':reference['fill_edges'],'comparison_edges':reference['winner_compare_edges'],'backend_edges':reference['busy_edges'],'serial_ns':(reference['fill_edges']+reference['busy_edges'])/.9},
  'I66_affine_publication':fast,'maximum8192_logical_rows_native_frames':{'rows':8192,'frames':len(fullcal['frames']),'max_frame_rows':max(f['rows'] for f in fullcal['frames']),'serial_edges':fullcal['serial_edges'],'serial_ns_at0p9GHz':fullcal['serial_ns_at0p9GHz']},
  'source_boolean_proof':'P1 source addr=obase+row; two distinct accepted row16 cannot alias in AW19 if whole extent in bounds. Guard accepts each orderedrow exactly once under frozenctx; no read or otherwriter allowed in affine frame. Required comparator19/equality and rowincrement16; no output payload or rounding change.',
  'new_control_cost_floor':{'full_phase_owner169_bits':169,'reset_era32_bits':32,'native_batch_nonce16_bits':16,'frame_row_offset16_bits':16,'expected_next_row16_bits':16,'controlvalid_poison4_bits':4,'additional_bits':253,'per_write_row16_vs_native_idx10_tag_extra_bits':6*593,'identity_association_not_native_epoch_only':True,'hold_mux_QNrestore_clockreset_and_compare_logic_unmapped':True,'contained_previous_state_credit':0},
  'positive_allowed_cell_guard_floor':guard_cost(),
  'forward_data_CDC_extension':data_CDC_cost(),'native_packet_ACK_bound':packet_ACK_native_bound(),
  'timing_join':{'native_backend_domain_GHz':.9,'native_read_capture_edges':4,'native_write_macro_visible_edges':2,'native_write_ACK_capture_edges':3,'positive_visible_to_captured_credit_required':True,'bank_rearm_not_VM_version_release':True,'VM_version_retire':'actual sameowner SUread + R+2 tag + source consumerdrain','source_relative_fence':'V<F; laterGU0>=F+1; adjacentSUfront>=F+7 under defaultoff matched publication hook','wholeprogram_absolute_F_and_deadline':None,'former7p888us_scalar_publication_screen_not_selected_native_service':True,'provider_frame_plus_reader_CRC_CDC_network_total_not_yet_admitted':True},
  'physical_contract':{'launcher':'tools/run_abi3_physical_aligned_guarded.py --macro-track-gate','main_policy_commit':'194417d02','aligned_hooks':'ot_mts::place + ot_mts::assert_on_track','abstract_selection':'v1 unchanged','v2_selected':False,'native_VM_component_expected_master_instances':{'ot_sram_1r1w_512x128_m4_r2c2':256},'full_field_context_additional_expected_master_instances':{'ot_rom_4096x274_m8':8192,'ot_rom_4096x72_m8':14336},'master_guard_not_actual_instance_census':True,'named_VM_home_clockreset_PG_OBS_and_decoder_local_paths_not_closed':True,'no_new_physical_job':True},
  'component_progress':'Native finite4edge read/3edge ACK source provider now bound; mandatory16lane-to512mask repair is ownerArch component, not a second VM RTL stream. Linear affine sourceguard is a proposed source-owned path; no generic winner-scan removal.',
  'admission':{'source_model_review':True,'engine_RTL_GO':False,'physical_GO':False,'full_token':False,'reason':'Need actual writer exclusion/dispatch reservation implementation, allowed-cell full guard construction and named native VM slot/clock/reset/routes; provider behavioral calendar not hardware timing.'}}

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path);ap.add_argument('--verify',action='store_true');args=ap.parse_args()
 if args.verify:
  for f,h in json.loads((OUT/'source_pins.json').read_text()).items():
   if hashlib.sha256((ROOT/f).read_bytes()).hexdigest()!=h:raise ValueError('source pin changed '+f)
  for f,h in json.loads((OUT/'manifest.json').read_text()).items():
   if hashlib.sha256((ROOT/f).read_bytes()).hexdigest()!=h:raise ValueError('artifact changed '+f)
  if json.dumps(generate(),sort_keys=True,indent=2)+'\n'!=(OUT/'model.json').read_text():raise ValueError('nonidentical native join regeneration')
  print('PASS source pins, artifacts and exact native VM join regeneration; NO HARDWARE ADMISSION')
 else:
  if args.out is None:ap.error('--out required for generation')
  args.out.write_text(json.dumps(generate(),sort_keys=True,indent=2)+'\n')
