#!/usr/bin/env python3
"""Source-bound reserved return landing and acyclic CKV lease phases; no timer-based progress claim."""
import argparse,hashlib,json,math,pathlib,subprocess
ROOT=pathlib.Path(__file__).resolve().parents[1];PIN='d2c28c279c4b8df731f9c4937e790831529a954b'
PATHS=['rtl/chip/ot_chip_v41x_ckv_die_service.sv','rtl/chip/ot_chip_v41x_ckv_sel_fetch.sv','rtl/chip/ot_chip_v41x_ckv_selected_dma.sv','rtl/chip/ot_chip_v41x_window_kv_prefetch.sv','rtl/chip/ot_chip_v41x_rope_hbm_cache.sv','rtl/chip/ot_chip_v41x_hbm_karb.sv','rtl/chip/ot_chip_v41x_kv_rope_reqmux.sv','rtl/chip/ckvsel/ot_chip_v41x_die.sv','rtl/chip/ckvsel/ot_chip_v41x_tile.sv','rtl/hdc/v41x/ot_hdc_v41x_idx_pool_adapt.sv','rtl/hdc/v41x/ot_hdc_v41x_idx_kstream_ring.sv','rtl/hdc/v41x/ot_hdc_v41x_idx_kstream.sv','rtl/hdc/v41x/ot_hdc_v41x_idx_ring_port.sv','rtl/hdc/v41x/ot_hdc_v41x_idx_ring_kwr.sv','rtl/hdc/v41x/ot_hdc_v41x_idx_pool_hbm_bridge.sv','rtl/w17_runtime/hdc/v41x/fastpp_pc21/l20/ot_hdc_core_v41x.sv','rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv','rtl/test/v41_runtime/w17_current_fastpp_die_rt.cpp']
def acyclic(edges):
 nodes={n for e in edges for n in e};remaining=set(nodes)
 while remaining:
  ready={n for n in remaining if not any(b==n and a in remaining for a,b in edges)}
  if not ready:return False
  remaining-=ready
 return True
def build():
 raw={p:subprocess.check_output(['git','show',PIN+':'+p],cwd=ROOT) for p in PATHS}
 def has(p,t):assert t.encode() in raw[p],(p,t)
 has(PATHS[0],'if (step && !go && id_done && enc_done)');has(PATHS[0],'go <= 1; f_job <= 1;')
 has(PATHS[9],'RING_WB=32, RING_GA=24');has(PATHS[10],'(nx_hi[p] - d_hi) < GA');has(PATHS[10],'assign rsp_rdy[gq] = (ahead < WB)')
 has(PATHS[11],'reg [4*DW-1:0] rob [0:NPC-1][0:WB-1]');has(PATHS[3],"assign s_rdy = 4'hf");has(PATHS[2],"assign s_rdy = 4'hf");has(PATHS[4],'assign rsp_rdy[s] = state == ISSUE || state == WAIT')
 has(PATHS[0],"assign c_srdy[st] = 1'b1");has(PATHS[17],'d->ckv_ag_tx_ready = 1')
 has(PATHS[12],"assign h_rsp_rdy[gi] = rsp_w[gi] ? 1'b1 : r_rsp_rdy[gi]");has(PATHS[13],"assign h_rsp_rdy[gp] = 1'b1")
 # Exhaustive modulo head/posted-lookahead landing and pair-slot uniqueness.
 checks=0
 for head in range(4096):
  slots=set()
  for ahead in range(24):
   block=(head+ahead)%4096;relative=(block-head)%4096
   assert relative<32 and block%32 not in slots;slots.add(block%32);checks+=1
 edges=[('old_epoch_jobs_retired','new_selection_ids'),('new_selection_ids','id_done'),('actual_row_produced','enc_done'),('id_done','request_quiesce'),('enc_done','request_quiesce'),('request_quiesce','block_new_jobs_keep_old_drains_enabled'),('block_new_jobs_keep_old_drains_enabled','prior_returns_and_writes_drained'),('prior_returns_and_writes_drained','exclusive_lease'),('exclusive_lease','write9_actual_burst_visible'),('write9_actual_burst_visible','publish_row'),('publish_row','new_f_job'),('new_f_job','gather'),('gather','attention'),('attention','consumer_finaldone'),('consumer_finaldone','next_epoch_credit')]
 assert acyclic(edges);assert not acyclic(edges+[('new_f_job','prior_returns_and_writes_drained')])
 negatives=['wait_new_fetch_before_lease_is_cycle','reset_ROB_head_while_old_returns_live','new_ID_table_overwrites_old_fetch','disable_return_ready_during_quiesce','publish_on_legacy_column_done','unreserved_AG_receiver_or_unbounded_externalready']
 read_terms=dict(REQ=10000,RAS=28125,RP=16250,RCDRD=19375,RFCPB=200000,CL=12500,BURST=1024,RSP=10000)
 read_envelope=sum(read_terms.values());qcost=2048*math.ceil(read_envelope*3/2500);response_tail=math.ceil((12500+1024+10000)*3/2500);landing=3072
 return dict(schema='opentallas.w17.ckv-prelease-return-contract.v1',status='SOURCE_BOUND_PHASE_AND_RESERVED_RECEIVER_MODEL_CONTRACT',source_pins={p:dict(commit=PIN,path=p,sha256=hashlib.sha256(b).hexdigest()) for p,b in raw.items()},
 actual_phase_finding='current id_done+enc_done simultaneously arms f_job and writer; must hold new f_job until exclusive lease plus9actualburstvisible writes; id/encoding do not require newCfetch',
 actual_receiver_bindings=dict(B_index_ring=dict(actual_WB=32,actual_GA=24,NPC=32,sectors_per_ROB_block_per_PC=4,ROB_capacity_sectors_per_stack=4096,ROB_bytes_per_stack=131072,max_posted_lookahead_sectors=3072,posted_bytes=98304,acceptance='returntag ahead<WB; every postedblock was reserved underahead<GA, independentlyofdownstream o_ready',retention='no scan_cmd/newhead reset untilalloldpostedresponses/counts retire; preserve ROB andepoch',port='one256bitsector/cycle/PC,32PCreturnlanding ports perstack',no_new_98KiB_payload_buffer_claim=True),
 B_migration=dict(ready='ring_port writer-tagbit12 routes h_rsp_rdy=1; migrationwriter gbuf17x256bits holdscurrentgroup',old_work='finisholdRFQ4 records withallmigrationread/write phases beforelease; notjustbackendqueueempty',max_migration_groups_per_record=6,read_sectors_per_group=17,write_sectors_per_group=17,max_RFQ4_migration_read_sectors=408,max_RFQ4_migration_and_key_writes=420),
 C_selected=dict(ready='c_srdy1 always; perpostedrow NSLOT64 reserves9sectors into2304bitrow slot',slot_total_sectors=576,slot_bytes=18432,output='ag_tx_ready external controls slot retirement only; postedreturnlanding stays enabled',old_jobs='finishpreviousfetch andackoldAG beforeoverwritingIDs; currentf_jobmuststayoffduringlease'),
 W_window=dict(ready='s_rdy4hf; issued/received17bits+epoch validateallocatedrow response',row_sectors=17,stage_lifetime='preserve row/user/epoch untilcomplete; two write phaseswaitdone; no resetinprelease'),
 P_rope=dict(ready='ISSUEorWAIT, reservedtwo256bitsectors/stack; transitionsIDLEonlyafterall8received',sectors_per_stack=2,old_jobs='allowoldISSUE requests andWAITreturns tofinish; blockonlynewpfcommand'),
 K_arbiter=dict(ready='directlowestreadyKresponsechannel perstack, one256bitsector/cycle; Bresponses forward perPC',PIPE_OUT=0,PIPE_RSP=0,finite_frozen_set='withno newrequests andallreservedKreceiversready, lowestpriority selection drainsNavailablebeatsinNedges; no starvation fromhigherthroughputnewrequests')),
 corrected_phase_dependencies=edges,negative_requirements=negatives,
 explicit_architectural_reservations=dict(quiesce='stopNEWcommands/descriptors butallowalreadyadmittedoldjobs toissuefinite remainingrequests andacceptresponses; afteroldjob retirementcloseallnewbackendenqueue anddrainfrozenqueues',not_snapshot_empty_only=True,IDtable='newsel_ready requirespreviousfetch/AGepochretired; existingpulse sel_v hasno ready, so compiler/runtime issueguard musthold it',AG='beforefetch starts reserve K512 unique rank slots ineachdestinationcollector plusfinitehop packetcredits; sourceacceptonlywhenall3 remote copies reserved and delivered underRamfinitecalendar',AG_current_host_ready1_is_not_bound=True,receiver_landing='acceptedrequest mustcarryexistingROB/rowslot reservation untilresponsecapture, never gate returnready onleasegrant/writercompletion',reserved_return_service='atleastone256bitsector/stack/fabriccycle whenreturnedvalid amongfrozenacceptedrequests;B hasactual32perPCports,K hasone; requirephysicalport/routing/clock budget inRammodel',external_ready='ifno finite reservedreceiver/transport calendar, cannotadmit lease; no timeout substitutesforcredit'),
 pricing=dict(accepted_backend_queue_bound_beats_per_stack=2048,return_queue_bound_beats_per_stack=1024,total_accepted_queued_or_return_bound=3072,landing_calendar_service_cycles=landing,landing_calendar_ns=landing*5/6,landing_calendar_bits_per_cycle_per_stack=256,four_parallel_stacks_aggregate_bits_per_cycle=1024,source_port_max_B_return_bits_per_cycle_per_stack=8192,not_extra_buffer_storage=True,
 read_service_candidate_terms_ps=read_terms,read_service_candidate_envelope_ps=read_envelope,queued2048_serial_read_candidate_cycles=qcost,latest_alreadycolumn_issued_response_tail_cycles=response_tail,coarse_frozen_queue_candidate_pluslanding_cycles=qcost+response_tail+landing,coarse_candidate_ns=(qcost+response_tail+landing)*5/6,
 envelope_scope='conditionalRamconservative perbank-refresh candidate, not proven controller upper; price remainingoldproducerwork/routing/registers/CDC separately. Acceptedqueue3072 is not totaloldjob demand. At intended id_done barrier current indexscan alreadyretired; enforce hardware phaseproof ratherthanblindlychargeallscansagain',actual_remaining_oldjobs_census_required=True,physical_endpoint_reservation_admitted=False),
 validation=dict(modulo_head_postedblock_checks=checks,phase_DAG_acyclic=True,new_fetch_wait_cycle_rejected=True,scope='source-token and scalarreservation/phase proof only, no actualRTLdrain or latencymeasurement'),RTL_changed=False,hardware_jobs_launched=0,launch_allowed=False,adopt=False)
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--out',type=pathlib.Path,required=True);a=ap.parse_args();r=build();assert not a.out.exists();a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r['pricing'],indent=2))
