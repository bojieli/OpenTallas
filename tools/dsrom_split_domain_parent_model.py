#!/usr/bin/env python3
"""Prospective DS two-clock parent construction, fixed PAR2 graph; no engine RTL.
Extract named source ports, bind clocks and finite protocol costs. No phase/MCP
exceptions or historical4/5-cycle service credit. Geometry admission is separate.
"""
import collections,gzip,hashlib,json,math,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'results/uarch/dsrom_split_domain_parent_20261003'
P=dict(X_SEL=1,X_EG=0,INSTR_BITS=2048,FULL_SHAPE=1,W=16,G=4,IL=8,BL=16,QLB=272,AW=30,NW=21,PAW=14,MP=1,SW=8,SUN=256,SUM=64,HS=8,HNL=3,HHW=8,HBAW=16,MG=8,MBAW=18,PIKH_HAW=30,ROM_R=128,ROM_PHW=6,ROM_VRD=64,HDIM=512,TOPK=512,XU_KW=12,NSLOT=1,XSQ=4,XSW=16,VM_AW=19,CL_TAGW=32,CL_PW=547,CL_FW=512,N_TP=4,PKG_DIES=2,MAXU=866,DESTS=64,LAW=12,PROG_AW=14,LWIN=10,QLIST_BITS=160)
P['ROM_FBW']=sum([1,P['ROM_PHW'],3,1,1,1,8,3,2,256,10,256,10,3,3,1,3,4,32,1024]);P['ROM_FRW']=128*69
P['ATT_TW']=1+16+1+512*16+1+4+4*16*265+1+1+32*16+1
P['ATT_FW']=4+16+4+4*16*32+4*16+2+8+4*16*16*32+4*16*16

def load(p):
 b=p.read_bytes();b=gzip.decompress(b) if p.suffix=='.gz' else b
 return [json.loads(line) for line in b.splitlines() if line.strip()] if '.jsonl' in p.name else json.loads(b)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def source(index):
 row=load(BASE/'inputs/origins.json')[index];return (BASE/'inputs'/row['copy']).read_text()
def ports(text,params):
 text=re.sub(r'/\*.*?\*/','',text,flags=re.S);text=re.sub(r'//[^\n]*','',text)
 start=text.index(') (')+3;header=text[start:text.index(');',start)];out={};carry=None
 for frag in header.split(','):
  frag=frag.strip();m=re.match(r'(input|output|inout)\s+(?:wire|reg|logic)\s*(?:signed\s*)?(\[[^\]]+\])?\s*(\w+)\s*$',frag)
  if m:
   dr,dim,name=m.groups();bits=1
   if dim:
    hi,lo=dim[1:-1].split(':');env=dict(params,clog2=lambda x:max(0,(x-1).bit_length()))
    def expr(t):
     t=t.replace('$clog2','clog2')
     if '?' in t:
      # Only source FULL_SHAPE conditional dimensions, no inferred values.
      t=re.sub(r'\(FULL_SHAPE\s*\?\s*(\d+)\s*:\s*(\d+)\)',lambda m:m[1] if params['FULL_SHAPE'] else m[2],t)
     return eval(t,{'__builtins__':{}},env)
    bits=int(expr(hi)-expr(lo)+1)
   carry=(dr,bits);out[name]=dict(direction=dr,bits=bits)
  elif re.fullmatch(r'\w+',frag) and carry:out[frag]=dict(direction=carry[0],bits=carry[1])
  else:raise ValueError('Unparsed source port: '+frag)
 return out

def signal_widths(text,params,names):
 """Bind command members to actual resolved source registers, not ISA proxy."""
 text=re.sub(r'/\*.*?\*/','',text,flags=re.S);text=re.sub(r'//[^\n]*','',text)
 out={};wanted=set(names)
 for match in re.finditer(r'\b(?:wire|reg)\s*(\[[^\]]+\])?\s*([^;]+);',text[text.index(');')+2:]):
  dim,decl=match.groups()
  for part in decl.split(','):
   n=re.match(r'\s*(\w+)',part)
   if not n or n[1] not in wanted:continue
   width=1
   if dim:
    hi,lo=dim[1:-1].split(':');width=eval(hi,{'__builtins__':{}},params)-eval(lo,{'__builtins__':{}},params)+1
   out[n[1]]=int(width)
 missing=wanted-set(out)
 if missing:raise ValueError('Unbound resolved command signals '+str(sorted(missing)))
 return out

def role(name):
 if name.startswith(('xs_vi','xs_rd','xs_vm','xs_res','vs_','vi_','vw_su','vw_rd','crom','xcrom','prog','vh_','ww_h')):return 'chain_local'
 if name.startswith(('rom_fb','rom_fr','rom_ffault','att_to','att_from','att_packed','qrom','pikh','ikh','win_blk')):return 'stream_local_or_fast_service'
 if name.startswith(('rom_x','rom_v','rom_w','vx_','vw_me','vq_','wqr_','ww_q','coll_','pikw_','kv_we','kv_waddr','kv_wdata')):return 'cross_domain'
 if name.startswith(('vr_','wxr_','vsl_','vw_xe','ww_x','erom','ewrom','wrom','mb_','hb_','hrom')):return 'mixed_engine_subsplit_required'
 return 'control_or_external_boundary_requires_named_owner'

GROUPS=[
 ('field_x_request','F2S',['rom_xre','rom_xaddr']),('field_x_reply','S2F',['rom_xq']),
 ('field_expert_id_request','F2S',['rom_vre','rom_vaddr']),('field_expert_id_reply','S2F',['rom_vq']),
 ('field_visible_row_write','F2S',['rom_we','rom_waddr','rom_wdata']),
 ('ME_attn_index_x_request','F2S',['vx_re','vx_addr']),('ME_attn_index_x_reply','S2F',['vx_q']),
 ('ME_attn_index_result_write','F2S',['vw_me_we','vw_me_addr','vw_me_mask','vw_me_data']),
 ('QE_scalar_x_request','F2S',['vq_re','vq_addr']),('QE_scalar_x_reply','S2F',['vq_q']),
 ('QE_block_x_request','F2S',['wqr_re','wqr_addr']),('QE_block_x_reply','S2F',['wqr_q']),
 ('QE_result_write','F2S',['ww_q_we','ww_q_addr','ww_q_mask','ww_q_data']),
 ('index_key_publication','S2F',['pikw_v','pikw_stack_mask','pikw_csec','pikw_codes','pikw_ssec','pikw_sslot','pikw_scales']),
 ('SU_kv_writer','S2F',['xs_kv_we','xs_kv_waddr','xs_kv_wdata']),
 ('selector_score_request','F2S',['vsl_re','vsl_addr']),('selector_score_reply','S2F',['vsl_q']),
 ('XU_scalar_read_request','F2S',['vr_re','vr_addr']),('XU_scalar_read_reply','S2F',['vr_q']),
 ('XU_block_read_request','F2S',['wxr_re','wxr_addr']),('XU_block_read_reply','S2F',['wxr_q']),
 ('XU_scalar_write','F2S',['vw_xe_we','vw_xe_addr','vw_xe_data']),
 ('XU_block_write','F2S',['ww_x_we','ww_x_addr','ww_x_mask','ww_x_data']),
 ('collective_command','S2F',['coll_go','coll_op','coll_src','coll_dst','coll_ibase','coll_n','coll_k','coll_stride','coll_seq','coll_rnd']),
 ('collective_status','F2S',['coll_busy','coll_fault']),
 ('rope_request_release','S2F',['rope_pf_v','rope_pf_kind','rope_pf_pos','rope_pf_release']),
 ('rope_status','F2S',['rope_pf_rdy','rope_pf_done','rope_pf_fault']),
 ('CKV_selection','S2F',['ckv_sel_v','ckv_sel_ibase']),

]

def phase_census():
 inp=BASE/'inputs';rows=load(inp/'20_phase_shard_bindings.jsonl.gz');calls=load(inp/'21_native_shard_choices.jsonl.gz')
 worst=[]
 for s in (0,1):
  best=max(rows,key=lambda x:x['shards'][s]['output_rows']);n=best['rows_per_rank'];roots=[]
  for g in range(64*s,64*(s+1)):
   roots.append(sum(max(0,1+(n-1-(2*g+offset))//256) for offset in (0,1)))
  assert sum(roots)==best['shards'][s]['output_rows']
  # Bound every phase independently using exact original row modulo128
  maxroot=0
  for r in rows:
   assert r['ordered_global_row_tags_unchanged'] and r['row_cross_shard_K_reductions']==0
   n=r['rows_per_rank'];g=64*s
   maxroot=max(maxroot,sum(max(0,1+(n-1-(2*g+o))//256) for o in (0,1)))
  worst.append(dict(shard=s,max_total_rows=best['shards'][s]['output_rows'],max_rows_per_root=maxroot,phase=best['phase'],stage=best['stage'],alias=best['alias'],K=best['K'],original_row_stride=256,original_global_roots=[64*s,64*(s+1)],local_roots=64))
 return dict(phases=len(rows),AR_calls=len(calls),max_K=max(r['K'] for r in rows),worst=worst,compiled_maps_are_source_symbolic=True,current_PHW6_runtime_not_PHW10_product_executable=True)

def build():
 for r in load(BASE/'inputs/origins.json'):
  if sha(BASE/'inputs'/r['copy'])!=r['sha256']:raise ValueError('Source archive drift')
 core=ports(source(3),P);inventory={n:dict(v,clock_disposition=role(n)) for n,v in core.items()}
 for name in ('rom_xq','rom_we','xs_rd_q','xs_res_data','pikw_codes'):assert name in core
 pp=dict(P,ROM_R=64,ROM_PHW=10,ROM_FRW=64*69);pp['ROM_FBW']=P['ROM_FBW']+4
 selected=ports(source(3),pp)
 edges=[]
 for name,dr,members in GROUPS:
  width=sum(selected[n]['bits'] for n in members)
  # Independent physical endpoints: no mux compression credit, no shared bank.
  payload=width+48 # named epoch32, transaction16
  edges.append(dict(name=name,direction=dr,members=[dict(name=n,**selected[n]) for n in members],source_bits=width,packet_bits=payload,replicas_per_parent=1,
   proposed_launch_capture_data_FF=2*payload,local_queue_FF_bits=8*payload,minimum_wire_tracks=payload,
   rate_words_per_hyperperiod=3,hyperperiod_ns='10/3',payload_bytes_per_accept=width/8,maximum_payload_bytes_s=width/8*900000000,
   outstanding_credit_seats=8,prospective_service='Dedicated named endpoint, not free VM/macro ports. Source synchronous read latency must become tagged reply-valid or engine preload barrier; accepted request alone never advances loader.',
   finite_bound='At most8queued packets; grant service one packet per destination cycle when epoch live and endpoint bank reservation active. Planned controller guarantees, not inferred current service.',
   output_visibility='Write commit at actual chain VM edge then tagged visibleACK reverse; ready/idle depends on ACK plus engine drain, not bridge enqueue.',current_ready_reply_valid_ports_exist=False))
 # External adapters have actual additional VM ports, separate from core header.
 coll=ports(source(14),dict(WA=15,FW=512,TAGW=32,N=4,GW=4,RB=2))
 ckv=ports(source(16),dict(K=512,POS_W=21,AW=30,VWA=15,HAW=30,TAGW=16,NSLOT=64,KW=10))
 for owner,table,groups in (
  ('collective',coll,[('read_request','F2S',['vm_re','vm_raddr']),('read_reply','S2F',['vm_rq']),('write4','F2S',['vm_we4','vm_waddr4','vm_wdata4'])]),
  ('CKV_service',ckv,[('id_read_request','F2S',['vm_re','vm_raddr']),('id_read_reply','S2F',['vm_rq'])]),
  ('rope_cache_snapshot',dict(cache_valid={'bits':1},cache_hold={'bits':1},cache_kind={'bits':1},cache_pos={'bits':21},cache_pairs={'bits':2048}),[('lease_reply','F2S',['cache_valid','cache_hold','cache_kind','cache_pos','cache_pairs'])]),
  ('package_host',dict(read_enable={'bits':1},address={'bits':15},data={'bits':512}),[('read_request','F2S',['read_enable','address']),('read_reply','S2F',['data']),('write','F2S',['read_enable','address','data'])]),
 ):
  for suffix,dr,members in groups:
   width=sum(table[n]['bits'] for n in members);payload=width+48
   edges.append(dict(name=owner+'_'+suffix,direction=dr,source_bits=width,packet_bits=payload,members=[dict(name=n,**table[n]) for n in members],replicas_per_parent=1,proposed_launch_capture_data_FF=2*payload,local_queue_FF_bits=8*payload,minimum_wire_tracks=payload,outstanding_credit_seats=8,rate_words_per_hyperperiod=3,hyperperiod_ns='10/3',payload_bytes_per_accept=width/8,maximum_payload_bytes_s=width/8*900000000,current_ready_reply_valid_ports_exist=False,source_basis='Native adapter ports; package xa widths from frozen die declarations',visibility='Actual chain VM commit -> tagged ACK; no acceptance/drain equivalence'))
 # Send actual resolved registered engine operands, not a stand-in raw ISA.
 commands={
  'field':['qe_xbase','qe_nb','qe_wbase','qe_ind','qe_ibase','qe_istride','qe_obase','qe_unrounded','me_k','me_split','me_wbase','me_xbase','me_xks','me_xcs','me_xjs','me_obase','me_ots','me_ojs','me_round','me_amax','me_mmode','mx_m','mx_xps','mx_ops'],
  'ME_attention_index':['me_nout','me_tiles','me_k','me_wbase','me_ts','me_ks','me_js','me_xbase','me_xks','me_xjs','me_xcs','me_hg','me_ogs','me_round','me_obase','me_ots','me_ojs','me_mmode','me_oen','me_fuse','me_wts','mx_m'],
  'QE':['qe_mode','qe_fp4','qe_unrounded','qe_xbase','qe_nb','qe_nout','qe_tiles','qe_wbase','qe_ind','qe_ibase','qe_istride','qe_obase','mx_m','mx_xps','mx_ops'],
  'XU_fast_subtree':['xu_op','xu_src','xu_dst','xu_n','xu_k','xu_layer','xu_bf16','xu_tok','xu_first','xu_hslot','xu_sel_first'],
 }
 for engine,members in commands.items():
  widths=signal_widths(source(3),pp,members)
  # Two-bit command subtype routes original field q/m or ME class; one go.
  cmdwidth=3+sum(widths.values())
  for suffix,dr,width in (('command','S2F',cmdwidth),('completion','F2S',2+21+32+1+16+1)):
   payload=width+48
   edges.append(dict(name=engine+'_'+suffix,direction=dr,source_bits=width,packet_bits=payload,members=[dict(name=n,bits=widths[n]) for n in members] if suffix=='command' else [],replicas_per_parent=1,proposed_launch_capture_data_FF=2*payload,local_queue_FF_bits=8*payload,minimum_wire_tracks=payload,outstanding_credit_seats=8,rate_words_per_hyperperiod=3,hyperperiod_ns='10/3',payload_bytes_per_accept=width/8,maximum_payload_bytes_s=width/8*900000000,source_basis='Actual resolved source registers plus go1/subtype2; completion ready/idle2, argmax idx21/value32/any1, progress16/fault1. Persistent XU hash/reset state remains chain-local; only fast subtree command crosses.',current_ready_reply_valid_ports_exist=False))
 # All named payload queues need a priced reverse credit/visible receipt.
 # Lane bitmap on writes allows ACK only when every enabled lane committed.
 for edge in list(edges):
  bitmap=64 if edge['name']=='field_visible_row_write' else 4 if edge['name'] in ('ME_attn_index_result_write','collective_write4') else 1
  width=4+1+1+1+bitmap # free seats, committed, fault, epoch drained, lane bitmap
  packet=width+48
  edges.append(dict(name=edge['name']+'_reverse_receipt',direction='S2F' if edge['direction']=='F2S' else 'F2S',source_bits=width,packet_bits=packet,members=[],replicas_per_parent=1,proposed_launch_capture_data_FF=2*packet,local_queue_FF_bits=8*packet,minimum_wire_tracks=packet,outstanding_credit_seats=8,rate_words_per_hyperperiod=3,hyperperiod_ns='10/3',payload_bytes_per_accept=width/8,maximum_payload_bytes_s=width/8*900000000,source_basis='New prospective receipt; no current port. Credit on freed queue seat; visible-write ACK requires every enabled lane at actual VM edge; engine retirement remains distinct.',current_ready_reply_valid_ports_exist=False))
 peer=load(BASE/'inputs/23_Epicurus_CKV_model_r3.json')
 peer_sources=load(BASE/'inputs/24_Epicurus_CKV_origins.json')['origins']
 peer_service=next(r for r in peer_sources if r['path']=='rtl/chip/ot_chip_v41x_ckv_die_service.sv')
 if peer_service['sha256']!=sha(BASE/'inputs/16_ot_chip_v41x_ckv_die_service.sv'):raise ValueError('Peer CKV equations do not bind this retained service')
 for edge in edges:
  if edge['name'].startswith(('XU_','selector_')):
   edge['mode_condition']='OP_SEL=0 with X_SEL!=0 and i_bf16: streaming subtree only. OP_SINK=1 and OP_EHASH=2 stay chain-local. X_EG=0 in frozen driver; no speculative fast gather admission. Mixed endpoint routing must isolate each active source mode before RTL.'
 census=phase_census();bits=sum(e['proposed_launch_capture_data_FF']+e['local_queue_FF_bits'] for e in edges)
 # Master body from actual retained LEF. Reservations are explicit proxies.
 lef=load(BASE/'inputs/22_cell_LEF.json.gz');dims={}
 for n in ('DFFHQNx1_ASAP7_75t_R','BUFx4_ASAP7_75t_R'):
  x,y=re.search(r'\bSIZE\s+(\S+)\s+BY\s+(\S+)\s*;',lef[n]).groups();dims[n]=float(x)*float(y)
 journal=64*64*69;state=bits+journal;clockbuf=math.ceil(state/8)
 construction=dict(default_off_parameter='DS_SPLIT_DOMAINS=0',new_parent_ports=['clk_stream','clk_chain','rst_stream_n','rst_chain_n','flush_req','flush_ack','epoch[31:0]'],
  streaming_hz=1200000000,chain_hz=900000000,common_PLL='3.6GHz /3,/4 phase relation must be parent-source bound',
  ownership=dict(chain=['sequencer and decoded fields','VM read/write commit','SU/vector/SFU/reducers','HE/HCP serial chain','XU Sinkhorn/hash controller'],stream=['ROM adapter+spine+complete field','QE/QDQ','attention adapters/tiles/staging','pooled index scan and HBM endpoints','BF16 selector fast subtree; Engram remains current X_EG0 path','collective engine/router/HBM service']),
  control='Atomic decoded command members from source per-engine ports, transaction16 + epoch32; no direct cross-clock go pulse, ready/idle/fault/argmax/completion. Command and visible completion reverse channels required.',
  bridge='Preselect source payload into dedicated source-clock FF; unconditional destination-clock input FF; queue/feedback/mux only inside destination domain. Direct crossing has no4:1array mux or enable-feedback mux. All data/control/credit crossings timed SS60/FF25 at full related clocks; no multicycle/phase exception.',
  rhythm='F2S acceptance limited3/4 fast edges and S2F3/3 chain edges, <=0.9Gsame-width packets/s. Phase-qualified valid/credits require common reset alignment; no single-clock proof. Backpressure through8finite seats, no perpetual4/3rate preservation claim.',
  pointer='Credit updates are registered source/destination full-clock paths, not combinational ready crosses. Overflow traps; new transaction cannot consume prior epoch reply.',
  reset='Stop new admissions -> drain accepted requests and actual visible writes/engine outputs -> exchange empty+retired epoch receipts -> flush local queues -> synchronize reset release in each domain -> latch fresh externally monotonic epoch32 -> exchange ready -> reopen. Forced reset aborts prior epoch and quarantines late service replies; no one-sided pointer reset or epoch reuse.',
  stalled_bound='For each reserved endpoint eight packets imply <=8 destination service cycles plus launch/capture/local queues, provided explicit grant/ready guarantee. Existing sources offer no universal finite consumer stall guarantee; external HBM/peer waits remain bound by their owner calendar, and timeout is fault, not successful completion.',
  field_result='ARreserve64rows/root*64roots raw69-bit entries BEFORE go; existing immutable stride256 bounds every symbolic phase. Capture accepts every source root result regardless of slow VM backpressure; new phase/reuse blocked until visibleACK drains all roots. No average-arrival assumption or full-return138469120-bit credit.',
  field_activation='ROM loader advances ld_k/ld_pos only on request accept; rq_* and quantizer metadata on matched reply-valid. Keep original have/s_ok/parity reuse and rounding. Dedicated64-element snapshot port, current one-cycle contract explicitly changed behind default-off.',
  CKV='Epicurus owns full512ready/gen/immutable lease successor. Boundary exports actual generation, accepted RX/staging, nine owner-visiblewrite ACKs and engine/output retirement. No mergerdone/producerempty/TXaccept as physical drain.',
  local_SUN_ports=dict(SU_read_request_bits=4*256*(1+30+2),SU_read_payload_bits=4*256*32,SU_indirect_request_bits=256*31,SU_indirect_payload_bits=256*32,SU_write_bits=256*63,reduction_write_bits=32*63,CDC_required=False,physical_VM_ports_not_inferred_free=True))
 model=dict(schema='DS_SPLIT_DOMAIN_PARENT_INVENTORY_AND_CONSTRUCTION_V1',source_main='09984efcab74873e6e03352607ab3d2c6442eccb',candidate='DS4096-TP4-S58-PAR2-NP2048',current_runtime_profile=P,prospective_selected_profile=pp,current_named_core_ports=inventory,CKV_peer_binding=dict(commit='6675dc3c5b7235e6df8ce0b61f8b05091f00b2bb',model_sha256=sha(BASE/'inputs/23_Epicurus_CKV_model_r3.json'),retained_service_sha256=peer_service['sha256'],retained_service_hash_matches_peer=True,source_equations=peer['equations'],installed_binary_binding=peer['scope']['installed_binary_binding'],successor_owner='Epicurus',trace_owner='Hubble',visible_write_and_CDC_calendar_owner='Maxwell',no_engine_jobs=True,selection_lifetime=peer['occupancy']['lifetime'],remote_RX_ports={n:v for n,v in ckv.items() if n.startswith('ag_rx')},generation_ready_additions_are_peer_owned=True),prospective_edges=edges,phase_source_census=census,construction=construction,
  target_applicability=dict(DS_ROM='Prospective selected PAR2 split parent only; no admission',DS_HBM='Same CDC correctness method; no ROM-specific area/topology transfer',Qwen_ROM='No DS selected-CKV/field transfer',Qwen_HBM='GPU organisation; no DS ROM topology transfer'),area=dict(actual_master_body_um2=dims,bridge_declared_state_bits=bits,AR_fullphase_journal_bits=journal,new_state_bits_floor=state,state_cell_floor_mm2=state*dims['DFFHQNx1_ASAP7_75t_R']/1e6,clock_sink_groups8_floor=clockbuf,clock_buffer_floor_mm2=clockbuf*dims['BUFx4_ASAP7_75t_R']/1e6,
   reserve_basis='State+clock master-body FLOOR only; mux/select/credit/reset/epoch/control cells, pin escape/PG/routing and HE/CROM adapters charged separately. No speculative removal or embedded credit.',
   full_return_storage_retained_bits=138469120,full_return_storage_credit_bits=0),
  compute=dict(bridge_MACs_per_cycle=0,bridge_compute_intensity_MAC_per_byte=0,field_arithmetic_unchanged=True,aggregate_compute_reduction_credit=0),routing=dict(sum_independent_crossing_signal_tracks=sum(e['minimum_wire_tracks'] for e in edges),assumed_multiplexing_credit=0,return_capture_native_bits_per_fast_cycle=4416,selected_physical_corridor_slot=None,physical_site_or_PG_capacity_claim=False,global_epoch_flush_reset_rail_tracks_additional=True,track_total_is_independent_signal_sum_not_one_shared_channel_fit=True,write_completion_ACK_and_reverse_credit_state_priced=True,credit_arbitration_epoch_reset_logic_cell_cost_not_yet_mapped=True),
  latency=dict(historical_fixed4_5_replaced_by='Per-edge launch/capture, accepted-request/response queues, bank service and actual visibleACK; source/load/return loops all composed.',
   AR_field_activation_K6144=dict(beats64=96,chain_port_service_ns=96/0.9,fast_original_port_service_ns=96/1.2,port_rate_delta_ns=96/0.9-96/1.2),
   AR_worst_phase_return=dict(rows_per_root=64,arrival_burst_fast_ns=64/1.2,VM_drain_chain_ns=64/0.9,maximum_drain_tail_if_serial_after_capture_ns=64/0.9,can_overlap_with_capture=True,overlap_credit_requires_finite_schedule=True),
   conservative_endpoint_pending8_service_ns=dict(F2S=8/0.9,S2F=8/1.2),composed_token_extension='Join at each source issue/read/return/visible completion graph event; do not sum1149calls serially or substitute modeled4/5for stalledservice.',current_fulltoken_calendar_not_replayed=True,rate_and_credit_contract_is_prospective_not_source_guarantee=True,per_phase_result_journal_AR_only=True,MTP_capacity_or_calendar_not_admitted=True),
  required_before_engine_G0=[dict(datum='Exact installed caller source/binary/defines/currentprogram+lease and actual stall/read/capture/writevisible/engineoutput trace',owner='Hubble',reason='StaticFASTPP profiles frozen; installed build must not be assumed identical.'),dict(datum='One selected co-resident slot/track/clockPG union for explicit bridge state+all named command/ACK/control routes',owner='Archimedes with Maxwell',reason='This construction adds state and crossings; no corridor borrowing or sourcearea credit.'),dict(datum='Actual bounded VMbank grant and return-visibleACK callback homes/generation',owner='Archimedes prospective arbiter + Maxwell owner calendar',reason='Source arrays expose ports, not actual SRAM/multiport implementation.'),dict(datum='Full512CKV receive/staging lease+visibleownerwrites+consumer retirement contract',owner='Epicurus',reason='6675sourcefailures retained; nonoverlapping implementation ownership.'),dict(datum='Fast-subtree versus slow-Sinkhorn XU source dispatch and persistent hash/reset isolation implementation proof',owner='Archimedes',reason='Mixed source module cannot be assigned one clock blindly.')],
  admission=dict(inventory_and_prospective_model_ready=False,engine_RTL_admitted=False,physical_build_admitted=False,hardware_closure_not_prerequisite_to_sized_RTL=True,reason='Named complete port/descriptor/control/slot and finite bank-grant contracts must finish G0; then RTL may be written before physical closure. SS/FF in actualparent required for adoption.'),live_global_solver_unchanged=True,no_new_PVE2_PVE3_jobs=True,no_element_reframe=True,new_engine_RTL=False)
 BASE.mkdir(parents=True,exist_ok=True);(BASE/'model.json').write_text(json.dumps(model,indent=2,sort_keys=True)+'\n');return model
if __name__=='__main__':
 m=build();print(json.dumps(dict(ports=len(m['current_named_core_ports']),edges=len(m['prospective_edges']),area=m['area'],routing=m['routing'],admission=m['admission']),indent=2))
