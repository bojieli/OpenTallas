"""Actual static-FP32 TOKX producer and finite held adapter enrollment; no RTL."""
import argparse, ast, collections, hashlib, json, math
from pathlib import Path
import ds_mtp_accept_leaf_model as L
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/uarch/ds_mtp_tokx_enrollment_20261003'
SOURCE=['tools/hdc_program_v41.py','tools/hdc_isa_v41.py',
'rtl/w17_runtime/hdc/v41x/ot_hdc_core_v41x.sv','rtl/hdc/v41x/ot_hdc_v41x_xu_adapt.sv',
'rtl/hdc/v41/ot_hdc_v41_xu.sv','rtl/hdc/v41/ot_hdc_select.sv',
'rtl/hdc/ot_hdc_accept.sv','rtl/test/tb_hdc_core_v41_mtp.sv','rtl/w17_runtime/chip/ot_chip_v41x_tile.sv',
'rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv','tools/ds_mtp_accept_leaf_model.py',
'results/uarch/ds_mtp_accept_leaf_20261003/model.json']

def source_branch():
 p=(OUT/'inputs/tools/hdc_program_v41.py').read_text()
 tree=ast.parse(p)
 method=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='draft_body')
 call=next(n for n in ast.walk(method) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)
           and n.func.attr=='xu' and any(k.arg=='xu_k' and isinstance(k.value,ast.Constant) and k.value.value==1 for k in n.keywords))
 kw={k.arg:ast.unparse(k.value) for k in call.keywords}
 assert 'xu_d_n' not in kw and kw['xu_n']=='0 if off else nv'
 core=(OUT/'inputs/rtl/w17_runtime/hdc/v41x/ot_hdc_core_v41x.sv').read_text()
 adapter=(OUT/'inputs/rtl/hdc/v41x/ot_hdc_v41x_xu_adapt.sv').read_text()
 assert "xu_bf16 <= (`F(XU_D_N) != 0)" in core
 assert '(X_SEL != 0 && i_bf16) ? S_XS0 : S_SEL' in adapter
 assert '.IW(16)' in adapter and '.in_idx(s_idx[15:0])' in adapter
 return dict(draft_keywords=kw,actual_count_dynamic=False,actual_scores='FP32',
 actual_branch='S_SEL scalar ot_hdc_select IW16 for both X_SEL0 and X_SEL1',
 earlier_468c_IW20_draft_mapping='SUPERSEDED: IW20 branch is dynamic-count BF16 only',
 required_repair='full scalar NW21 input/index/comparator/emission/output/writeback/sel_first, unchanged K/VW/ORDER; no truncated16 zeroextension')

def scalar_bits(k,iw):
 kw=math.ceil(math.log2(k+1));pw=32+iw+2
 fields={'input_stage':2+32+iw+kw,'key_stage':pw,'wave_and_threshold':2*k,
         'insertion_store':k*pw,'registered_pass':(k-1)*pw,
         'emission_bank':k*(iw+2),'controller_and_output':kw+iw+10}
 return fields,sum(fields.values())

class ProducerHolders:
 """Four protected source records, no sidecar unpriced fault/phase registers.

 begin is the accepted command origin; finish is matching producer terminal.
 Refused event changes no accepted debt and must drive leaf caller_bad.
 This is a model contract, not installed XU/ME generation echo.
 """
 def __init__(self):
  self.words={k:L.encode64(0) for k in ('tokx_value','tokx_origin','amax_value','amax_origin')}
 def read(self,kind):
  data=[];bad=False
  for suffix,bits in [('value',22),('origin',29)]:
   raw,corrected,ue=L.decode64(self.words[kind+'_'+suffix]);bad|=ue or bool(raw>>bits);data.append(raw)
  val,origin=data
  bad|=(val&L.MASK)>=L.VOCAB or bool((val>>21)&1 and not (origin>>28)&1)
  return {'token':val&L.MASK,'fresh':bool((val>>21)&1),'lease':(origin&L.MASK,(origin>>21)&15),
          'slot':(origin>>25)&7,'occupied':bool((origin>>28)&1),'bad':bool(bad)}
 def begin(self,kind,lease,slot):
  r=self.read(kind);pos,gen=lease
  if r['bad'] or r['occupied'] or not 0<=pos<=L.MASK or not 0<=gen<16 or not (1 if kind=='tokx' else 0)<=slot<8:return False
  # Validate before any write: busy origin cannot overwrite a held selected token.
  self.words[kind+'_origin']=L.encode64(pos|(gen<<21)|(slot<<25)|(1<<28))
  self.words[kind+'_value']=L.encode64(0)
  return True
 def finish(self,kind,lease,slot,token):
  r=self.read(kind)
  if r['bad'] or not r['occupied'] or r['fresh'] or r['lease']!=lease or r['slot']!=slot or not 0<=token<L.VOCAB:return False
  self.words[kind+'_value']=L.encode64(token|(1<<21));return True
 def request(self,kind):
  r=self.read(kind)
  return None if r['bad'] or not r['occupied'] or not r['fresh'] else (r['lease'],r['slot'],r['token'])
 def take(self,kind,lease,slot):
  r=self.read(kind)
  if r['bad'] or not r['occupied'] or not r['fresh'] or r['lease']!=lease or r['slot']!=slot:return False
  self.words[kind+'_origin']=L.encode64(0);self.words[kind+'_value']=L.encode64(0);return True

def model():
 pins=json.loads((OUT/'input_manifest.json').read_text())
 for r in pins:assert hashlib.sha256((OUT/r['archive']).read_bytes()).hexdigest()==r['sha256'],r['path']
 old=json.loads((OUT/'inputs/results/uarch/ds_mtp_accept_leaf_20261003/model.json').read_text())
 prices=json.loads((L.OUT/'inputs/results/uarch/w2_pc_exact_completion_20261003/inputs/cell_prices.json').read_text())['facts']
 # Exact raw register width change, unchanged full source TOPK512 default, not K1.
 k=512;before=scalar_bits(k,16);after=scalar_bits(k,21);delta=after[1]-before[1]
 g=L.Gates()
 # Conservative width-only construction: 5 extra unsigned-comparison stages per real compare,
 # each stage <=12 NAND+8INV; no sharing. Four bank update choices and insertion keep/pass.
 g.nand(12*5*(k+k-1));g.inv(8*5*(k+k-1))
 g.mux(5*k,2);g.mux(5*(k-1),2);g.mux(5*k,4);g.inv(5*k)
 scalar=collections.Counter(g.dict());scalar['DFFASRHQNx1_ASAP7_75t_R']+=delta
 scalar['INVx1_ASAP7_75t_R']+=delta;scalar['BUFx4_ASAP7_75t_R']+=2*delta+2*L.buffers(delta)
 # Replace caller73raw/3records by102raw/4records. Leaf614raw unchanged.
 # Conservative add-only gate screen retains all old guard costs and adds enlarged-key/freshness guards.
 g=L.Gates();g.codec()
 for _ in range(4):g.eq(29)
 g.AND(32);g.OR(24);g.mux(72,4);g.mux(72,2)
 extra=collections.Counter(g.dict());extra['DFFASRHQNx1_ASAP7_75t_R']+=72
 extra['INVx1_ASAP7_75t_R']+=72;extra['BUFx4_ASAP7_75t_R']+=144+2*L.buffers(72)+2*L.buffers(58)
 totals=collections.Counter(old['cell_counts_total']);totals.update(extra)
 def area(c):return sum(v*prices[n]['SS']['area_um2'] for n,v in c.items())
 extra_body=area(extra);body=old['gross_cell_body_um2']+extra_body
 slot=dict(old['physical_slot']);slot.update(actual_reserved_rectangle=None,actual_legal_channel_tracks=None,
   requested_height_um=math.ceil(body/.5/128/.27)*.27,minimum_50pct_cell_area_mm2=body/.5/1e6,
   requested_owner_slot='MTP_ACCEPT_SERIAL_SPINE_PER_ACTUAL_CORE',fit_qualified=False)
 return dict(schema='DS_MTP_ACTUAL_TOKX_KERNEL_ENROLLMENT_R1',default_enable=False,source_pins=pins,
 source_selected_producer=source_branch(),actual_runtime={'tile_core_NSLOT_override':None,'core_default_NSLOT':1,'candidate_NSLOT8_installed':False,'source_default_scalar_K':512,'whole_MTP_actual_selected_fullshape_K_override':None,'no_undersized_instance_claim':True},kernel={'NSLOT':8,'NW':21,'class':'A current greedy prefix+bonus','whole_MTP_qualification':False,'MACs_per_cycle':0},
 scalar_repair={'source_default_K':k,'runtime_draft_k':1,'VW':32,'ORDER':1,'old_IW':16,'new_IW':21,
 'raw_before_by_register':before[0],'raw_after_by_register':after[0],'raw_before':before[1],'raw_after':after[1],
 'raw_FF_width_delta':delta,'width_only_cell_counts':dict(scalar),'width_only_body_um2':area(scalar),
 'width_only_50pct_mm2':area(scalar)/.5/1e6,'scope':'unmapped conservative width-only screen; NOT complete protected scalar selector or physical admission',
 'protection_of_all_mutable_selector_records':'required, absent from original; exact codeword packing/checked pipeline must be priced before connected build',
 'source_latency_after_last_input_edges':2*k+2,'input_scores_per_edge':1,'input_bytes_per_edge':4,
 'source_vm_write_bytes_per_edge':4,'no_new_selector_replica':True,'source_input_clock_and_loaded_SS_FF':None,
 'prospective_width_added_edges':0,'zero_added_edges_is_proven':False,'all_added_checked_stages_must_be_priced':True},
 source_holders={'value':{'token':21,'fresh':1},'origin':{'position':21,'generation':4,'slot':3,'occupied':1},
 'replicas_each':2,'raw_bits':102,'protected_words':4,'protected_bits':288,
 'begin':'accepted XU/ME command captures full origin before launch; TOKX destination slot is draft row+1, AMAX verify destination exact lane/slot',
 'finish':'terminal full token plus original echoed lease/slot; wrong/duplicate terminal refuses without mutating debt and drives leaf caller_bad',
 'take':'held matching leaf input handshake only; source holder free is not KV release',
 'source_generation_echo_installed':False,'source_multi_lane_ME_stamp_mapping':None,
 'existing_core_c_slot_r_reused_as_origin':False,'one_holder_per_kind':True,
 'no_hidden_latest_lease_at_return':True},
 kernel_composition={'previous_raw':687,'new_raw':614+102,'raw_delta':29,'previous_protected':1944,'new_protected':2016,
 'added_protected_bits':72,'once_only':'replace old caller73raw/3words by102raw/4words, keep leaf614raw once; do not add old whole kernel again',
 'cell_counts_total':dict(totals),'add_only_conservative_cell_counts':dict(extra),'gross_cell_body_um2':body,
 'gross_50pct_mm2':body/.5/1e6,'matched_old_accept_select_and_selector_net_debit':None},
 ports={'leaf_union_signals':636,'producer_to_holder_cut_per_kind':51,'producer_to_holder_cut_instances':2,
 'cut_fields':'token21,originallease25,slot3,valid1,ready1; prelaunch begin separately serialized on these fields with named control not counted as free',
 'begin_finish_discriminator_per_kind':1,'producer_adapter_signals_per_kind_total':52,
 'leaf_nominal_ingress_II_edges':2,'source_adapter_same_kind_occupancy':1,'whole_draft_II':None,
 'held_core_CTL':'S_ISSUE holds decoded command and does not advancePC until exact acceptance; source identity must match heldCTL slot',
 'output_occupancy':1,'result_ACK':'S_ACC consumes stable prefix; S_RST restoration must sample before matchingresulttake; localACK notrollback'},
 clock={'kernel_GHz':.9,'SS_setup_uncertainty_ps':60,'FF_hold_uncertainty_ps':25,'accept_to_done_min_edges':3,
 'delta_vs_old_leaf_edges':2,'delta_ns':2/.9,'producer_finish_to_first_leaf_query_min_edges':1,
 'source_last_input_to_result_min_edges':2*k+2,'producer_wait_fence_and_backpressure_edges':None,
 'protected_sinks':2016,'SS_unbuffered_clock_fF':2016*prices['DFFASRHQNx1_ASAP7_75t_R']['SS']['pins']['CLK']['cap_fF'],
 'FF_unbuffered_clock_fF':2016*prices['DFFASRHQNx1_ASAP7_75t_R']['FF']['pins']['CLK']['cap_fF'],
 'sameclock_kernel_only':True,'actual_XU_ME_core_clock_bindings':None,'CDC_cost_if_domains_differ':None,
 'loaded_codec_selector_paths_or_closure_proven':False},
 physical_slot=slot,
 enrollment={'minimal_defaultoff_kernel':'model-sized separate component handoff; must replace callerledger with this r1',
 'connected_actual_producer':'FAIL until scalarNW21 repair, protectedproducer stages, actual origin/slot/gen echo and heldCTL wiring',
 'physical':'PENDING_ARCHIMEDES_NAMED_RECTANGLE_CHANNEL_CLOCK_RESET_AND_LOADED_CUTS',
 'RTL_build_launched':False,'rate_claim':None,'missing_whole_drafter_blocks_kernel_component':False,
 'nativecalendar_or_acceptance_work_duplicated':False},
 peer_dependencies={'Archimedes':['one concrete core/context and replica count','disjoint rectangle and legal tracks for636 leaf and2x52 producer cuts afterPG/via/clock','0.9GHz sinktree/load/reset/skew with60/25 uncertainties','actualproducer clocks and pricedCDC or explicitsameclockenrollment','checkedprefix/codec cuts before launch'],
 'implementation_owner':['defaultoff kernel parameter withNSLOT8NW21 fullwidth fixture','source scalarIW21 throughin/out/writeback comparator bank notjustwire','registered origin/token freshness and heldready interfaces','originalsource pins unchanged; separate newRTL source successor aftermodelenrollment'],
 'Dewey_Popper':['actualpositiveallcopies fence incllaunchstamp/return/result/reverse/reset endpoints','nativecaller origin/lane identity and reuse mapping, no invented calendar'],
 'Claude':['acceptance and complete drafter remain separatelyowned, no rate inference from leaf tests']})

def main():
 p=argparse.ArgumentParser();p.add_argument('--verify',action='store_true');p.add_argument('--out',type=Path);a=p.parse_args()
 data=(json.dumps(model(),indent=2,sort_keys=True)+'\n').encode();dest=a.out or OUT/'model.json'
 if a.verify:assert dest.read_bytes()==data;print('PASS byte-exact source-selected scalar TOKX/kernel enrollment; physical/source connection pending')
 else:dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data);print(dest)
if __name__=='__main__':main()
