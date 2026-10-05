#!/usr/bin/env python3
"""Size mandatory L20 repairs and prepare immutable source-only control fixtures.

Executes a finite contract oracle using the pinned burst visibility model, never
RTL or DRAM scheduling. Positive model cases do not qualify a corrected source.
Source copies are prepared only after the model record exists and is checked.
"""
import argparse
import ast
import hashlib
import json
import math
import subprocess
from pathlib import Path

REAL='4e38326d6f361bc85e660f48c59c355e2bb95274'
BASE='e72abea5ae169d3167dddc89543013f0e6bb3a7a'
PREV='117ae7d5d25fda1084402c456340f2861eb32d1f'
BACKEND='6e1158394262bc47773993e04efce0672ac4552e'
PINS={}
CACHE={}
ROOT=Path(__file__).resolve().parents[1]
COPIES=[
 'rtl/chip/ot_chip_v41x_kv_reqmux.sv', 'rtl/chip/ot_chip_v41x_kv_rope_reqmux.sv',
 'rtl/chip/ot_chip_v41x_ckv_die_service.sv','rtl/chip/ot_chip_v41x_ckv_sel_ids.sv',
 'rtl/chip/ot_chip_v41x_ckv_sel_fetch.sv','rtl/chip/ot_chip_v41x_ckv_selected_dma.sv',
 'rtl/chip/ot_chip_v41x_ckv_fp4_decode.sv','rtl/chip/ot_chip_v41x_ckv_stream_merge.sv',
 'rtl/chip/ot_chip_v41x_ckv_row_encoder.sv','rtl/chip/ot_chip_v41x_attn_desc_lifecycle.sv',
 'rtl/hdc/v41/ot_hdc_fp4qdq.sv','rtl/hdc/v41/ot_hdc_v41_qe.sv','rtl/hdc/ot_hdc_delay.sv']


def read(rev,path):
 key=rev+':'+path
 if key not in CACHE:
  raw=subprocess.check_output(['git','show',key],cwd=ROOT)
  CACHE[key]=raw.decode();PINS[key]=dict(commit=rev,path=path,sha256=hashlib.sha256(raw).hexdigest())
 return CACHE[key]


def record(rev,path):return json.loads(read(rev,path))


def cite(path,needle):
 hits=[dict(line=i,text=s.strip()) for i,s in enumerate(read(REAL,path).splitlines(),1) if needle in s]
 assert hits,(path,needle)
 return dict(pin=REAL+':'+path,matches=hits)


class Contract:
 """Finite control oracle, with no payload decode/re-encode or RTL authority."""
 def __init__(self):
  self.epoch=0;self.rows={};self.reserved=False;self.visible=set();self.pending=None
  self.published=False;self.window=False;self.peer=[None]*3;self.peer_inflight=[0]*3
  self.complete_jobs=0;self.desc_drained=False;self.writes_quiet=False
 def begin(self):
  if self.epoch and not self.retired():raise ValueError('previous epoch not retired')
  self.epoch+=1;self.rows={};self.visible=set();self.pending=None
  self.published=self.window=False;self.reserved=True;self.complete_jobs=0
  self.desc_drained=self.writes_quiet=False
 def accept_write(self,k):
  if self.pending is not None or k in self.visible or not 0<=k<9:raise ValueError('write owner/sector')
  self.pending=k
 def acknowledge(self,k,event):
  if not isinstance(event,dict) or 'visible_ps' not in event or event.get('sector')!=k or self.pending!=k:
   raise ValueError('not actual owned visibility')
  self.visible.add(k);self.pending=None;self.published=len(self.visible)==9
 def receive(self,epoch,rank,gid,expected_gid):
  if epoch!=self.epoch or not self.reserved or not 0<=rank<512 or rank in self.rows or gid!=expected_gid:
   raise ValueError('epoch/rank/GID/reservation')
  self.rows[rank]=gid
 def tx(self,peer,rank):
  if self.peer[peer] is not None or self.peer_inflight[peer]>=512:raise ValueError('finite TX credit')
  self.peer[peer]=(self.epoch,rank);self.peer_inflight[peer]+=1
 def delivered(self,peer):
  if self.peer[peer] is None:raise ValueError('no TX skid')
  self.peer[peer]=None
 def returned(self,peer):
  if self.peer_inflight[peer]==0:raise ValueError('unowned reverse credit')
  self.peer_inflight[peer]-=1
 def ready(self):return self.window and self.published and len(self.rows)==512
 def retired(self):
  return (self.complete_jobs==2 and self.desc_drained and self.writes_quiet and self.pending is None
          and not any(self.peer) and not any(self.peer_inflight))


def reject(fn):
 try:fn()
 except ValueError:return True
 raise AssertionError('Illegal boundary accepted')


def oracle():
 source=read(BACKEND,'tools/common_hbm_backend_provider_contract.py')
 env={'__name__':'pinned_contract_only','__file__':str(Path(__file__).resolve())}
 exec(compile(source,'pinned_backend_contract','exec'),env)
 b=env['BurstVisibilityModel'](capacity_sectors=1<<24)
 c=Contract();c.begin();trace=[];neg={}
 for k in range(9):
  b.preload(k,bytes(32));data=bytes([k+1])*32
  assert b.reserve(k,k,data)==k;c.accept_write(k)
  neg['grant_is_not_publication']=not c.published
  assert not c.published
  neg['grant_ACK_rejected']=reject(lambda:c.acknowledge(k,None))
  b.WR_issue(k,k,b.now);scheduled=b.take_scheduled(k)
  neg['column_ack_rejected']=reject(lambda:c.acknowledge(k,scheduled))
  due=scheduled['column_ps']+7274
  while b.now<due:
   assert b.memory[k]==bytes(32) and b.peek_visible(k) is None
   b.tick()
  assert b.memory[k]==data
  neg['wrong_owner_visible_ACK_rejected']=reject(lambda:c.acknowledge((k+1)%9,b.peek_visible(k)))
  event=b.peek_visible(k);b.tick(3)
  assert b.peek_visible(k)==event and c.pending==k
  accepted=b.take_visible(k);c.acknowledge(k,accepted)
  neg['duplicate_visible_ACK_rejected']=reject(lambda:c.acknowledge(k,accepted))
  assert c.published==(k==8)
  trace.append(dict(sector=k,column_ps=scheduled['column_ps'],burst_due_ps=due,
                    actual_visible_ps=event['visible_ps'],row_published=c.published))
 neg['only_eight_ACKs_not_published']=not trace[7]['row_published']
 for rank in range(511):c.receive(1,rank,1000+rank,1000+rank)
 c.window=True;assert not c.ready()
 neg['WINDOW128_plus_selected511_not_READY']=True
 neg['wrong_epoch_rejected']=reject(lambda:c.receive(0,511,1511,1511))
 neg['wrong_GID_rejected']=reject(lambda:c.receive(1,511,1512,1511))
 c.receive(1,511,1511,1511);assert c.ready()
 neg['duplicate_rank_rejected']=reject(lambda:c.receive(1,0,1000,1000))
 for peer in range(3):c.tx(peer,511)
 neg['TX_skid_overflow_rejected']=reject(lambda:c.tx(0,0))
 for peer in range(3):c.delivered(peer)
 c.complete_jobs=2;c.desc_drained=c.writes_quiet=True
 assert not c.retired();neg['delivery_without_reversecredit_not_retired']=True
 neg['next_selection_before_retirement_rejected']=reject(c.begin)
 for peer in range(3):c.returned(peer)
 assert c.retired();c.begin();assert c.epoch==2 and len(c.rows)==0 and not c.ready()
 neg['selection_epoch_and_npresent_reset']=True
 neg['old_reply_after_new_selection_rejected']=reject(lambda:c.receive(1,0,1000,1000))
 # Cold reset must prove old backend/peer work drained before opening epoch1;
 # never claim that clearing a local counter flushes an external provider.
 return dict(verdict='PASS_FINITE_REQUIREMENTS_ORACLE_NOT_CONNECTED_SOURCE_GATE',
             write_events=trace,negative_cases=neg,post_retirement_epoch=c.epoch,
             source_backend_class='BurstVisibilityModel: actual supplied column events, not DRAM scheduler',
             synthetic_sector_patterns=True,activation_injection=False,decode_reencode=False,
             qualified_scope='Nine-sector visibility/finite ownership and boundary rejection oracle only',
             corrected_mux_or_service_RTL_qualified=False,full640_producer_qualified=False)


def build():
 old=record(PREV,'results/uarch/dsrom_attention_controller_l20_composition_20261001/model.json')
 assert old['source_binding']['L20_source_count']==125 and old['program_provenance']['instructions']==144
 schema=read(BASE,'tools/uarch_model.py');tree=ast.parse(schema)
 attention=None
 for node in ast.walk(tree):
  if isinstance(node,ast.Assign) and isinstance(node.value,ast.Call) and isinstance(node.value.func,ast.Name) and node.value.func.id=='dict':
   for target in node.targets:
    if isinstance(target,ast.Subscript) and isinstance(target.value,ast.Name) and target.value.id=='out' and isinstance(target.slice,ast.Constant) and target.slice.value=='attention':attention=node.value
 assert attention
 keys=[k.arg for k in attention.keywords]
 unit=record(BASE,'results/arch/arch_budget_v41.json')['unit_areas_um2']['mac_bf16_um2']
 floorplan=next(node.value for node in tree.body if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='FLOORPLAN' for t in node.targets))
 hub=next(ast.literal_eval(k.value) for k in floorplan.keywords if k.arg=='hub_mm2')
 fullslot=record(BASE,'results/quality/w16_w17_fullslot_composition_20261001/composition.json')
 bfspare=float(fullslot['mapped_BF_baseline']['conditional_clock_slot_stdcell_spare_um2'])
 for p in COPIES:read(REAL,p)
 direct_port=dict(codes=128,scales=16,block=4,GID=21,user=10,layer=6,epoch=16,valid=1)
 width=sum(direct_port.values())
 # Keep prior metadata budget and add direct packed producer pipe+16-block
 # bitmap, stable published-count+lease/refusal/fault/reset flags. Existing
 # own row2304 and collector147456B seats already charged in payload ledger.
 mandatory_state={k:v for k,v in old['added_opt_in_register_budget']['fields'].items() if k!='controller_cut'}
 mandatory_state.update(direct_packed_sideband_pipeline=width,own_block_capture_mask=16,
                        published_source_count=21,lease_and_reset_flags=16)
 mandatory_bits=sum(mandatory_state.values())
 std=mandatory_bits*.2916
 backend=old['physical_budget']['backend_additional_area_mm2']
 frontend_mux_std=1152*.2/1e6
 mandatory_placed=std/.5/1e6+backend+frontend_mux_std/.5
 cut_bits=old['added_opt_in_register_budget']['fields']['controller_cut']
 cut_std=cut_bits*.2916
 payload=dict(old['storage_bits_per_die'])
 legacy=payload.pop('own_capture_and_encoder_and_encoded_buffers')
 payload['direct_quantizer_packed_own_row_buffer']=2304
 mux=old['combinational_budget']
 read_mux=mux['collector_four_read_mux_bit_equivalents']
 write_mux=mux['collector_five_write_candidates_bit_equivalents']
 muxbits=read_mux+write_mux+mux['fetch_four_stack_64slot_request_mux_bit_equivalents']+mux['selectedID_five_read_mux_bit_equivalents']+16960
 cell_total=64*512*unit+sum(payload.values())*.2916+muxbits*.2+std
 # backend footprint uses50%placement; subtract itsFF area only if rebuilding
 # its gate cost. Here retain footprint separately and never sum ascellarea.
 baseline_plus_repair_placed=cell_total/.5/1e6+backend+frontend_mux_std/.5
 candidate= dict(element=old['source_binding']['real_commit']+':rtl/hdc/v41x/ot_hdc_v41x_attn_tile.sv',
    replicas=64,rows_per_cycle=4,products_per_cycle=32768,
    ports_total=dict(q_bits=8192,kv_in_bits=16960,p_in_bits=512,pv_out_bits=32768),stationary_banks=3,
    area_element_um2=512*unit,area_basis='source unified-model MAC estimate; no hardened tile record or real controller slot fit',
    hardened=False,area_mm2=round(64*512*unit/1e6,9),
    ops={'L20.attn.scores':dict(beats=160,positions=1,issue=160,tile_latency=33),
         'L20.attn.pv':dict(beats=160,p_words=320,pwords_per_cycle=1,positions=1,issue=320)},
    measured_job_cycles=None,measured=dict(record='results/rtl/v41_full_attention_numeric/result.json',
      record_pwords2='results/rtl/w11_attn_ploader.json',job_cycles_pwords2={640:449,128:193},
      verify6={1:3389,2:2429},job_cycles_pwords1=609,pv_window_pwords1=[248,559]))
 assert set(candidate)==set(keys)
 variants=[
  dict(path='rtl/w17_runtime/l20_exact/ot_chip_v41x_kv_reqmux.sv',module='ot_chip_v41x_kv_reqmux_l20_exact',base=COPIES[0],parameters={'CKV_WRITE_VISIBLE':0},repair='WritableC data/strb/WE, registered W/C ownership retained through actual visible event; default legacy branch'),
  dict(path='rtl/w17_runtime/l20_exact/ot_chip_v41x_kv_rope_reqmux.sv',module='ot_chip_v41x_kv_rope_reqmux_l20_exact',base=COPIES[1],parameters={'CKV_WRITE_VISIBLE':0},repair='Allow legal Cwrite through outer tagguard; propagate ownerACK and all original read tags; default unchanged'),
  dict(path='rtl/w17_runtime/l20_exact/ot_chip_v41x_ckv_die_service.sv',module='ot_chip_v41x_ckv_die_service_l20_exact',base=COPIES[2],parameters={'CKV_SERVICE_EXACT':0},repair='Direct packed-row producer; ninevisibleACK fence; epoch/seat/peercredit; priority selectionclear; no legacyencoder on enabled path'),
  dict(path='rtl/w17_runtime/l20_exact/ot_chip_v41x_die.sv',module='ot_chip_v41x_die_l20_exact',base='rtl/chip/ckvsel/ot_chip_v41x_die.sv',parameters={'CKV_SERVICE_EXACT':0},repair='WINDOW128+selected512 jointREADY640, fault propagation, exact retirement/resetdrain; retain L0 path'),
  dict(path='rtl/w17_runtime/l20_exact/ot_hdc_fp4qdq.sv',module='ot_hdc_fp4qdq_l20_exact',base=COPIES[10],parameters={'CKV_PACKED_SIDEBAND':0},repair='Expose original roundedscale decision and S5sign/code at S6valid, preserving BF16outputs/order; no inversion of dequantized BF16'),
  dict(path='rtl/w17_runtime/l20_exact/ot_hdc_v41_qe.sv',module='ot_hdc_v41_qe_l20_exact',base=COPIES[11],parameters={'CKV_PACKED_SIDEBAND':0},repair='144bit code+scale and identity sideband forPC38, same quantizer acceptance/valid; reserve complete row before no-stall quantizer command'),
  dict(path='rtl/w17_runtime/l20_exact/ot_hdc_core_v41x.sv',module='ot_hdc_core_v41x_l20_exact',base='rtl/w17_runtime/hdc/v41x/fastpp_pc21/l20/ot_hdc_core_v41x.sv',parameters={'CKV_SERVICE_EXACT':0},repair='Credit guard beforePC38/PC53; propagate identity and packedproducer, preserve144ISA encodings'),
  dict(path='rtl/w17_runtime/l20_exact/ot_chip_v41x_tile.sv',module='ot_chip_v41x_tile_l20_exact',base='rtl/chip/ckvsel/ot_chip_v41x_tile.sv',parameters={'CKV_SERVICE_EXACT':0},repair='Connect sideband/core/die, no SUactivation injector'),
  dict(path='rtl/w17_runtime/l20_exact/ot_chip_v41x_idx_hbm.sv',module='ot_chip_v41x_idx_hbm_l20_exact',base='rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv',parameters={'BURST_VISIBLE_WRITES':0},repair='Actual tcol captured beforepop; update backing atCWL+BURST; heldscheduled/visible events, forwarded exactclock, fulladdress capacity; oldbranch retained'),
  dict(path='rtl/test/v41_runtime/ot_v41_rt_die_l20_exact.sv',module='ot_v41_rt_die_l20_exact',base='rtl/test/v41_runtime/ot_v41_rt_die_l20.sv',parameters={'CKV_SERVICE_EXACT':0},repair='Source-select corrected services and clock provider; runtime/peerdriver to reserve finite hopcalendar; full runtime not prepared or launched')]
 for v in variants:read(REAL,v['base']);v['source_pin']=PINS[REAL+':'+v['base']]
 bench=dict(schema='opentallas.dsrom.L20-isolated-correctness-fixture-plan.v1',
    first_experiment=dict(name='C_WRITE_SUPPRESSION_AND_GRANT_VS_VISIBLE',source_files=COPIES[:2],
       current_expected='Cread accepted; inner Cwrite emitsWE0/ACK0; outer rejectsCwrite andfaults',
       corrected_expected='Each Csector address/data/strb intact; grants/columns do notpublish; ninth uniqueactualvisibleACK publishes',
       backend='ActualimmutableRTL backend when qualifying correctedsource. Supplied-column BurstVisibilityModel onlyforcontractoracle; not an admittedcompletepath.',
       drive='Generated9sector256bitpatterns, no weight/KVcheckpoint, activation, compressedrowdecode or reencode',
       observe=['Cvalid/ready','masterWE/address/data/strb','W/Cowner','actual WRscheduled','actual backingupdate','WRvisible accepted','rowpublish']),
    next_experiments=[
      dict(name='EPOCH_RESET_AND_COUNTER',check='Two selections, no stalecounter from laterNBA; rejectwrong/duplicateepoch/GID; busyreset requires backend+peerdrain before opening next epoch'),
      dict(name='JOINT_READY640',check='WINDOW128 and511selected remainsnotREADY;512correctranks+visibleownrow+nofault raisesREADY once matchingdescriptor generation'),
      dict(name='FINITE_PEER_CREDIT',check='512seat cap/rank;3single-rowTXskids; sourceaccept requiresall3copy reservations; delivery alone cannotreturnepochcredit'),
      dict(name='QK_PV_RETIREMENT',check='160orderedall1beats eachop; originalbankguards/credits; actualMEidle/VMwritequiet andDRAIN->IDLE before selectionreuse; FINALSU/RoPE retirement remainsprogramdependency'),
      dict(name='DIRECT_PC38_PRODUCER',check='Realquantizer roundedscale/code sideband exact vs golden, all16blocks,identity/valid aligned. Legacyrowencoder forbidden in enabledpath; no standalone reencode accepted as completed producer.')],
    execution='PREPARED_ONLY_NO_RTL_SIMULATION',compiler_scope='At most mux/service/control/producer unit bench per experiment; no fullchip/runtime elaboration, engine build, or physical job',
    compile_commands_not_executed=[['iverilog','-g2012','-s','tb_l20_write_visibility','-o','isolated_mux_sim','tb_l20_write_visibility.sv',*COPIES[:2]]],
    original_modules='Immutable negative witnesses; hypothetical corrected variantfiles are declared only, not authored.',
    source_copies_after_model=True,admitted_complete_path=False,
    planned_bench_files=['rtl/test/w17/tb_l20_write_visibility.sv','rtl/test/w17/tb_l20_ckv_joint_service.sv'],
    corrected_connected_top_edges=[
       'actualQDQ4Esideband -> QE/core/tile -> owned2304bitcapture',
       'rowwritevalid/data/strb -> writableC innerKV -> outerRoPE -> actualHBMkarb/backend',
       'actualbackingupdate -> heldWRvisible -> W/Cowner -> nine-sectorrowpublished',
       'selectionIDs+epoch ->512rankseats ->64DMArowcredits ->3TXskids ->finitepeerprovider',
       'peeraccept+epoch ->collector ->reversecredit ->TXreservationrelease',
       'WINDOW128validated + selected512present + ownrowpublished ->generationmatchedREADY640',
       'QK160beats ->actualconsumercomplete ->PV160beats ->DRAIN/MEidle/writequiet ->epochreuse'],
    refused_complete_path=['legacyreencoder','goldenactivationinjector','grant/columnvisibility','hostready1/unboundeddeque','syntheticengineidleorfixeddeadline','unboundphysicalclock/routecapacity'])
 citations=dict(
   inner_write_suppressed=cite(COPIES[0],"assign m_we[s] = choose_w ? w_we[s] : 1'b0"),
   outer_write_rejected=cite(COPIES[1],'&& !c_we[s]'),
   grant_release=cite(COPIES[2],"wr_k == 4'd8"),
   counter_override=cite(COPIES[2],'npresent <= npresent +'),
   counter_clear=cite(COPIES[2],'present <= 0; npresent <= 0; rel_on <= 0; tail <= 0;'),
   QDQ8_only=cite(COPIES[11],'kvb_v <= aq_vo && mode == QDQ8'),
   QDQ4E_codes=cite(COPIES[10],'s5_c[i] <= cc;'),
   QDQ4E_scale=cite(COPIES[10],'s5_n[b] <= s4_n[b]'),
   QDQ4E_valid=cite(COPIES[10],'vo <= s5_v;'),
   scope_partialREADY=cite('rtl/chip/ckvsel/ot_chip_v41x_die.sv',".stage_rows(WINDOW_HBM_ATTENTION ? 11'd128"))
 return dict(schema='opentallas.dsrom.L20-mandatory-service-repair-fixture-model.v1',
    status='MANDATORY_CORRECTNESS_MODEL_AND_FIXTURE_PREPARED_SOURCE_REPAIR_NOT_QUALIFIED',
    model_review_ready=True,engine_RTL_build_ready=False,full640_source_correct=False,launch_allowed=False,
    original_failure=old['original_failure'],prior_model_pin=PINS[PREV+':results/uarch/dsrom_attention_controller_l20_composition_20261001/model.json'],
    preserved_inputs=dict(source_commit=REAL,L20_source_count=125,program_instructions=144,
      original_program_sha256=old['program_provenance']['current_program_sha256'],all125_source_manifest=old['source_binding']['sources'],original_program_unchanged=True),
    mandatory_vs_timing=dict(mandatory='WritableC, actualburstpublication, originalQDQ4Epackedproducer, epoch/seat/retirement correction. Required correctnessrepair; >=1%performance lever gate doesnot apply.',
      common_cut='Separate opt-in, default0, prospectivecommon2cycles retained. No cut needed to demonstrate write/visibility correctness; no clock/SSFF qualification fromfixture.',mandatory_default_off=True),
    proposed_exact_variant_files=variants,variant_sources_authored=False,
    actual_uarch_schema_binding=dict(pin=PINS[BASE+':tools/uarch_model.py'],function='dedicated_ledger',attention_keys=keys,
      schema_compatible_attention_entry=candidate,original_uarch_model_edited=False,
      additive_service_entry=dict(element='L20mandatory CKVpublication/epoch/peerjoin services',replicas=1,
         ports_total=dict(packed_producer_bits=width,packed_producer_payload_bits=144,peer_packet_bits=2351,peer_replicas=3,
                          selected_to_merger_bits=9216,engine_packed_bits=16960,HBM_sector_bits=256,HBM_stacks=4),
         area_mm2=mandatory_placed,area_basis='50%placement candidate, stdcell assumptions separatelypriced; no realcontextfit',
         ops={'L20.ckv.publication':dict(sectors=9,issue=9,visibility_candidate_cycles=2952)},
         composed_events=old['minimum_opt_in']['phase_dependencies']),
      generic_schema_depth33_is_not_actual_attention_valid_latency=True,
      consumer_override='Current 609cycle historical attention measurement isnot substitutedforactual4e383 postREADY2894/3374 envelopes; retainoriginalmeasuredrecord and bindadditiveeventcost explicitly.'),
    direct_producer=dict(port_fields=direct_port,bits_per_beat=width,payload_Bpc=18,beats_per_row=16,row_bits=2304,
      block_order='codeblock0..31 andscale0..31 fromactualQDQ4E decision; capturetwo16elementblocks/beat',
      reservation='Onecomplete2304bitrowseat reserved beforePC38; no-stall8cyclequantizer requiresall16outputs canland; holdidentity+producercredit throughninevisiblewrites',
      current_source_binding_missing='QDQ4Epacked sideband isabsent; QDQ8 kvb port isnot thisproducer. Newquantizer/QE/core/tileconnections require classA gate before correctedcompletepath admission.',
      removed_legacy_payload_bits=legacy-2304,legacy_reencoder_not_on_enabled_path=True,
      latency='Existing quantizerLAT8 retained; pack atsameS6valid, QEsideband alignment andservicecapture priced at2prospectivestreamcycles. No32cycleinverseencoder substituted.',
      additional_control_latency_cycles=2),
    finite_state=dict(mandatory_fields=mandatory_state,mandatory_added_bits=mandatory_bits,
      mandatory_stdcell_um2=std,backend_added_bits=8192,common_cut_bits=cut_bits,common_cut_stdcell_um2=cut_std,
      payload_bits=payload,total_listed_payload_bits=sum(payload.values()),
      seat_payload_bytes=147456,seats=512,skids=3,skid_bits_each=2352,
      credit_lifetime='Unique rankseat perselection;peercredit releasedafterdestinationaccept and reversecredit, epochreuse onlyafteroldpeerempty+bothjobsDRAIN+resultwritesquiet',
      reset='Shared synchronousservice reset cannot flushunresetbackend/peer work; holdnewselectionuntilactualdrained acknowledgments; generationwrap drains before16bitreuse'),
    area_against_slots=dict(unified_MAC_unit_um2=unit,attention64_tile_estimate_mm2=candidate['area_mm2'],
      mandatory_placement_candidate_mm2=mandatory_placed,
      L20_TP4_service_replicas=4,TP4_mandatory_placement_candidate_mm2=4*mandatory_placed,
      TP4_full_listed_attention_service_candidate_mm2=4*baseline_plus_repair_placed,
      common_cut_placement_candidate_mm2=cut_std/.5/1e6,
      full_listed_attention_service_candidate_mm2=baseline_plus_repair_placed,
      full_listed_with_common_cut_candidate_mm2=baseline_plus_repair_placed+cut_std/.5/1e6,
      utilization_assumed=.5,backend_placement_area_mm2=backend,frontend_owner_mux_only_placed_mm2=frontend_mux_std/.5,
      original_frontend_total_placed_mm2=.0004689648,
      correction='Prior117ae frontendmux-only subtraction removedoneFFarea froma50%placementfootprint; correctmux-only is.0004608mm2. Originalrecordretained; owner14FF alreadyincludedinmandatoryledger.',
      conditional_BF_pair_spare_stdcell_um2=bfspare,mandatory_newFF_vs_that_spare_pass=std<=bfspare,
      mandatory_newFF_spare_deficit_um2=std-bfspare,unified_shared_hub_envelope_mm2=hub,
      listed_total_vs_entire_hub_envelope_fraction=baseline_plus_repair_placed/hub,
      actual_attention_service_slot_fit='FAIL_USING_OLD_BF_SPARE; DEDICATED_HUB_SLOT_NOT_SOURCE_BOUND',
      full_goal_fit='HOLD: sharedhub233.7mm2 not allocatedattentionservice capacity. Fullindexedlayerincludesindex/SU/VM/RoPE/link/CDC/reset/clock/PG/othernonexperts. Must subtracttheirsourceboundreservations andbindreal4e383slots before engineRTL.',
      census_scope='MAC512estimate/tile + listedpayloadFF + explicitnaivemuxes + mandatorystate/backend. OmitsarithmeticnonMAC,reset/clock/hold/tree/control andphysicalrouting; no fitclaim.',
      macro_alternative=old['source_finite_producers']['source_macro_branch']),
    route_and_latency_contract=dict(routes=old['ports_and_routes'],additional_direct_producer_signal_tracks=width+1,
      source_input_peak_bytes_per_cycle=18,source_row_write_bytes=288,board_peer_required_bits_per_cycle=1176,
      service_candidate=old['finite_service_candidate'],QK_PV_envelopes=old['local_controller'],
      domain='Runtime sharedclk evidenceonly. Productstream1.2GHz/serial0.9GHz requiresactualCDC andreturncredit provider. Sidebandextra2streamcycles separatefromcontrollercut2.',
      capacity='No measuredrealenginechannel supplied; explicitwidths andaggregate replica demands retained, no stubpolyline orsharedhubcapacity transfer.'),
    first_contract_experiment=oracle(),source_citations=citations,bench_plan=bench,
    full640_admission_predicates=['allactualCwritepayloads passtwoactualmuxes','backendactualbackingcommit emitsheldvisibleevent',
      'directPC38codes/scales producerclassA, nolegacyreencoder','nineuniqueownedvisibleACKs thenpublish',
      'WINDOW128+selected512matchingepoch/GIDs+faultfree jointREADY','selectionclearpriority andold epochreset/drain',
      'all3peerTXcopies reservedandfinite512seatstiedtoreversecredit','160beatsQKthen160PV;DRAIN+MEidle+VMwritequiet;oldpeer/backendretired',
      'completeuarchservicecomposition andactualslot/route/CDC inputsreviewed'],
    four_target_applicability=old['four_targets'],
    operations=dict(RTL_authored=0,RTL_builds=0,full_builds=0,PnR=0,payload_checkpoint_reads=0,live_job_operations=0,source_copies_only_after_model=True),pins=PINS)


def emit(path,value):
 text=json.dumps(value,sort_keys=True,indent=2)+'\n'
 if path.exists() and path.read_text()!=text:raise SystemExit('Immutableoutputdiffers')
 path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text)


def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output',type=Path,required=True)
 ap.add_argument('--prepare-copies',type=Path);args=ap.parse_args()
 value=build();value['generator_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
 emit(args.output,value)
 if args.prepare_copies:
  # The model has now been emitted; copies haveoriginalbytes andmayserveonly
  # asnegativewitnesses/dependencies. No repairedRTL orbench compilation.
  assert json.loads(args.output.read_text())['model_review_ready']
  manifest=[]
  for path in COPIES:
   data=read(REAL,path).encode();dest=args.prepare_copies/'source'/path
   if dest.exists() and dest.read_bytes()!=data:raise SystemExit('Sourcecopydiffers')
   dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
   manifest.append(dict(source_pin=PINS[REAL+':'+path],copy=str(dest.relative_to(args.prepare_copies))))
  emit(args.prepare_copies/'bench_plan.json',value['bench_plan'])
  emit(args.prepare_copies/'source_manifest.json',dict(model_generator_sha256=value['generator_sha256'],
      model_record_sha256=hashlib.sha256(args.output.read_bytes()).hexdigest(),copies=manifest,
      corrected_sources=False,RTL_executed=False,scope='Exact sourcecopies forisolatednegativewitnessandfuturecontrol/servicefixture; noactivationpayload'))
 print(json.dumps(dict(status=value['status'],mandatory_bits=value['finite_state']['mandatory_added_bits'],
     mandatory_placed_mm2=value['area_against_slots']['mandatory_placement_candidate_mm2'],
     first_experiment=value['first_contract_experiment']['verdict'],engine_RTL_build_ready=False)))

if __name__=='__main__':main()
