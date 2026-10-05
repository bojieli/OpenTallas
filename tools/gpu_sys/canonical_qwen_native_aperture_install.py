"""Install real bank/collector/router in ONE r5 successor, retaining safety.

Unbound physical profile/controller ports are explicit, read-only to RPC SET,
so this source preparation cannot be admitted as a runnable native factory.
They must be replaced by Pauli's frozen actual modules before the sole build.
"""
import json,hashlib
from pathlib import Path
from tools.gpu_sys.canonical_qwen_manifest_install import once
from tools.gpu_sys.canonical_qwen_native_aperture_cluster import ports
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'rtl/model/qwen_hbm_banked_atomic_factory_20261003_r5'
BANK='rtl/experimental/canonical_qwen_native_apertures_20261003/ot_gpu_qwen_native_aperture_range_owner.sv'
COL='rtl/experimental/canonical_qwen_native_apertures_20261003/ot_gpu_qwen_native_aperture_collector.sv'
CLUSTER='rtl/model/qwen_native_aperture_cluster_20261003/ot_gpu_qwen_native_aperture_cluster.sv'
ROUTE='rtl/model/qwen_native_rf_route_20261003/ot_gpu_qwen_native_rf_route_r2.sv'
INITIAL='rtl/gpu/native/ot_gpu_qwen_initial_completion.sv'
def sha(p):return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
def generate(out):
 out=Path(out).resolve()
 if out.exists():raise ValueError('fresh successor required')
 b=json.loads((BASE/'ports.json').read_text());sv=(BASE/(b['top']+'.sv')).read_text();cpp=(BASE/'pin_driver.cpp').read_text();decl=[];extra=[];new={}
 sv=once(sv,'parameter bit ENABLE_BANK_BARRIER=0)','parameter bit ENABLE_BANK_BARRIER=0,parameter bit ENABLE_NATIVE_APERTURES=0)')
 sv=once(sv,'ot_gpu_qwen_banked_manifest_range_owner #(.ENABLE(ENABLE && ENABLE_MANIFEST && ENABLE_BANK_BARRIER),.SM_INDEX(i))','ot_gpu_qwen_native_aperture_range_owner #(.ENABLE(ENABLE && ENABLE_MANIFEST && ENABLE_BANK_BARRIER && ENABLE_NATIVE_APERTURES),.SM_INDEX(i))')
 def add(n,d,w,count=1,leaf=None,block='native_aperture',host=True):
  total=w*count;decl.append(f' {d} wire [{total-1}:0] {n}')
  new[n]=dict(direction=d,bits=total,count=count,leaf_bits=w,block=block,leaf=leaf or n,host_writable=d=='input' and host)
  return n
 add('native_apertures_enabled','output',1,1,'enabled','native_aperture_feature',False)
 extra.append('assign native_apertures_enabled=ENABLE && ENABLE_MANIFEST && ENABLE_BANK_BARRIER && ENABLE_NATIVE_APERTURES;')
 # Exact added bank ABI, queried roles/bounds are outputs, never host grants.
 old={p['leaf'] for n,p in b['pins'].items() if p.get('block')=='source_owner'};con=[]
 for n,p in ports(ROOT/BANK).items():
  if n in old or n=='clk':continue
  direction='output' if n=='native_rf_workspace_free' else p['direction'];target=add('source_owner_'+n,direction,p['bits'],64,n,'source_owner')
  con.append('.'+n+'('+target+('[i]' if p['bits']==1 else f'[i*{p["bits"]}+:{p["bits"]}]')+')')
 sv=once(sv,' u_source_owner(\n',' u_source_owner(\n '+',\n '.join(con)+',\n')
 original=(BASE/(b['top']+'.sv')).read_text()
 oldstart=original.index(' ot_gpu_qwen_banked_manifest_range_owner #')
 oldend=original.index('\n );',oldstart)+len('\n );')
 newstart=sv.index(' ot_gpu_qwen_native_aperture_range_owner #');newend=sv.index('\n );',newstart)+len('\n );')
 disabled=[]
 for n,p in ports(ROOT/BANK).items():
  if n not in old and n!='clk' and p['direction']=='output':
   alias='source_owner_'+n;sl=alias+'[i]' if p['bits']==1 else alias+f'[i*{p["bits"]}+:{p["bits"]}]'
   disabled.append('assign '+sl+"='0;")
 sv=sv[:newstart]+' if(ENABLE_NATIVE_APERTURES)begin:enabled_native_bank\n'+sv[newstart:newend]+'\n end else begin:original_banked_owner\n'+original[oldstart:oldend]+'\n'+'\n'.join(disabled)+'\n end'+sv[newend:]
 # Existing accepted private ACKs must not masquerade as canonicalRF child ACK.
 sv=once(sv,'assign source_owner_page_ack_valid[i]=sm_rf_ack_accept[i];','assign source_owner_page_ack_valid[i]=sm_rf_ack_accept[i] && (!ENABLE_NATIVE_APERTURES || sm_host_ack_slot[i*9+:9]>=9\'d32);')
 links={
 'query_empty':'native_bank_query_empty','clk':'stream_clk','por_n':'source_owner_por_n','warm_reset':'source_owner_warm_reset',
 'issuer_held_valid':'issuer_busy','issuer_held_fault':'issuer_fault','issuer_held_tuple':'issuer_publish_tuple','issuer_held_owner':'issuer_publish_owner',
 'query_valid':'source_owner_query_result_valid','query_retained':'source_owner_source_owner_retained','query_write':'source_owner_query_result_write','query_workspace':'source_owner_query_result_workspace','bank_fault':'source_owner_fault',
 'query_tuple':'source_owner_query_result_tuple','query_slot':'source_owner_query_result_slot','query_owner':'source_owner_query_result_owner','query_version':'source_owner_query_result_version','query_first':'source_owner_query_result_first','query_end':'source_owner_query_result_end',
 'bank_scope_valid':'source_owner_lease_scope_valid','bank_scope_writable':'source_owner_lease_scope_writable','bank_scope_workspace':'source_owner_lease_scope_workspace','bank_scope_tuple':'source_owner_lease_scope_tuple','bank_scope_owner':'source_owner_lease_scope_owner',
 'ack_accept':'sm_rf_ack_accept','ack_slot':'sm_host_ack_slot','ack_owner':'sm_host_ack_owner',
 'frame_accept':'actual_native_frame_accept','frame_tuple':'issuer_frame_retire_tuple','frame_owner':'issuer_frame_retire_owner',
 'rfroute_bank_rd_ready':'native_backend_rd_ready','rfroute_bank_wr_ready':'native_backend_wr_ready','rfroute_bank_rsp_valid':'sm_host_rsp_valid','rfroute_bank_rsp_a':'sm_host_rsp_a','rfroute_bank_rsp_b':'sm_host_rsp_b','rfroute_bank_ack_valid':'sm_host_ack_valid','rfroute_bank_ack_slot':'sm_host_ack_slot','rfroute_bank_ack_owner':'sm_host_ack_owner',
 'rfroute_bank_port_owned':'native_bank_port_owned','controller_private_RF_quiescent':'native_private_quiescent'
 }
 cluster=ports(ROOT/CLUSTER);cluster_book=json.loads((ROOT/CLUSTER).with_name('ports.json').read_text())['pins']
 for n,p in cluster.items():
  if n in links:
   if n.startswith('issuer_held_'):
    target='native_aperture_'+n
    add(target,'output',cluster_book[n]['leaf_bits'],64,n,'native_aperture')
    extra.append('assign '+target+'='+links[n]+';')
   continue
  target='native_aperture_'+n
  # Only source cursor/capture offers may be sent by source-owned frontend.
  host=n.startswith(('cursor_load_','capture_','begin_')) or n=='source_cursor_advance_ready'
  leaf=cluster_book[n];add(target,p['direction'],leaf['leaf_bits'],leaf['count'],n,'native_aperture' if leaf['count']==64 else 'native_RF_boundary',host)
  links[n]=target
  if p['direction']=='input' and not host:b['unresolved'].append('Physical producer input '+target+' must be bound to actual Pauli/profile/result source before fullbuild')
 extra+=['wire [63:0] actual_native_frame_accept=issuer_frame_retire_valid & issuer_frame_retire_ready;',
 'wire native_private_reservation=ENABLE_NATIVE_APERTURES && ((|native_aperture_source_cursor_valid)||(|native_aperture_context_live)||(|native_aperture_source_cursor_advance_valid));',
 'wire [63:0] native_bank_port_owned=source_owner_lease_scope_valid & ~tc_busy & ~tc_fault;',
 'wire [63:0] native_private_quiescent=rfdrain_w6_local_RF_empty & ~tc_busy & ~tc_fault;',
 'wire [63:0] native_backend_rd_ready,native_backend_wr_ready,raw_backend_rd_ready,raw_backend_wr_ready;',
 'wire [63:0] raw_tc_d_ready,raw_simd_ready;',
 'wire [63:0] native_external_read_admit,native_external_write_admit;',
 'wire [63:0] native_bank_query_empty;' ]
 # Same actual TC and legacy SIMD: stop NEW commands under coded reservation,
 # keep all old data/completion/debt drains unchanged.
 sv=once(sv,'.d_valid(tc_d_valid[i]),','.d_valid(tc_d_valid[i] && !native_private_reservation),')
 sv=once(sv,'.d_ready(tc_d_ready[i]),','.d_ready(raw_tc_d_ready[i]),')
 sv=once(sv,"assign tc_d_ready[i]='0;","assign raw_tc_d_ready[i]='0;")
 sv=once(sv,'.start(tc_start[i]),','.start(tc_start[i] && !native_private_reservation),')
 sv=once(sv,'.simd_valid(sm_simd_valid[i]),','.simd_valid(sm_simd_valid[i] && !native_private_reservation),')
 sv=once(sv,'.simd_ready(sm_simd_ready[i]),','.simd_ready(raw_simd_ready[i]),')
 extra+=['assign tc_d_ready=raw_tc_d_ready & {64{!native_private_reservation}};','assign sm_simd_ready=raw_simd_ready & {64{!native_private_reservation}};']
 # Real guarded RF single-port arbitration. Native route owns its accepted seat;
 # staging requests are admitted only against the actual retained Q workspace.
 for kind in ['rd','wr']:
  sv=once(sv,f'.host_{kind}_valid(sm_host_{kind}_valid[i]),',f'.host_{kind}_valid(native_aperture_rfroute_bank_{kind}_valid[i] || (sm_host_{kind}_valid[i] && native_external_'+('read' if kind=='rd' else 'write')+'_admit[i])),')
  sv=once(sv,f'.host_{kind}_ready(sm_host_{kind}_ready[i]),',f'.host_{kind}_ready(raw_backend_{kind}_ready[i]),')
 for leaf,width,kind in [('a',9,'rd'),('b',9,'rd'),('dst',9,'wr'),('wdata',4096,'wr'),('owner',46,'wr')]:
  native='wowner' if leaf=='owner' else leaf;target='native_aperture_rfroute_bank_'+native
  sv=once(sv,f'.host_{leaf}(sm_host_{leaf}[i*{width} +: {width}]),',f'.host_{leaf}(native_aperture_rfroute_bank_{kind}_valid[i] ? {target}[i*{width}+:{width}] : sm_host_{leaf}[i*{width} +: {width}]),')
 # Both source owner46 and full consumer root are actual coded observations.
 sv=once(sv,'.host_owner(native_aperture_rfroute_bank_wr_valid[i] ? native_aperture_rfroute_bank_wowner[i*46+:46] : sm_host_owner[i*46 +: 46]),',
 '.host_owner(native_aperture_rfroute_bank_wr_valid[i] ? native_aperture_rfroute_bank_wowner[i*46+:46] : native_aperture_rfroute_bank_pending_write[i] ? native_aperture_rfroute_bank_saved_read_owner[i*46+:46] : native_aperture_rfroute_bank_rd_valid[i] ? native_aperture_read_owner[(native_aperture_rfroute_bank_root_tuple[i*239+30+:6])*46+:46] : native_aperture_rfroute_bank_pending_read[i] ? native_aperture_rfroute_bank_saved_read_owner[i*46+:46] : sm_host_owner[i*46 +: 46]),')
 for kind,role in [('rd','read'),('wr','write')]:
  context='(native_aperture_rfroute_bank_'+kind+'_valid[i] || native_aperture_rfroute_bank_pending_'+role+'[i])'
  values={'binding_valid':'source_owner_lease_scope_valid[i] && !native_aperture_rfroute_route_fault[i]', 'KV_related':"1'b0", 'identity':'native_aperture_rfroute_bank_root_tuple[i*239+100+:64]', 'key':"20'b0", 'continuation_valid':('sm_rd_continuation_valid[i]' if kind=='rd' else 'sm_wr_continuation_valid[i]')}
  for field,value in values.items():
   w=64 if field=='identity' else 20 if field=='key' else 1
   old='sm_host_'+kind+'_'+field+('[i]' if w==1 else f'[i*{w} +: {w}]')
   sv=once(sv,'.host_'+kind+'_'+field+'('+old+'),','.host_'+kind+'_'+field+'('+context+' ? '+value+' : '+old+'),')
 for leaf in ['rsp','ack']:
  sv=once(sv,f'.host_{leaf}_ready(sm_host_{leaf}_ready[i]),',f'.host_{leaf}_ready((!ENABLE_NATIVE_APERTURES || native_aperture_rfroute_bank_routes_drained[i]) ? sm_host_{leaf}_ready[i] : native_aperture_rfroute_bank_{leaf}_ready[i]),')
 extra+=['for(genvar i=0;i<64;i=i+1)begin:native_real_private_reservation',
 ' wire private_held=native_aperture_context_live[i] && (|native_aperture_lease_workspace[i*5+:5]) && source_owner_workspace_held_valid[i] && native_aperture_authority_tuple[i*239+:239]==source_owner_workspace_held_tuple[i*239+:239] && native_aperture_authority_owner[i*55+:55]==source_owner_workspace_held_owner55[i*55+:55];',
 ' if(ENABLE_NATIVE_APERTURES)begin:actual_Q_empty_view',
 '  assign native_bank_query_empty[i]=g_source_owner[i].enabled_native_bank.u_source_owner.all_clean && !g_source_owner[i].enabled_native_bank.u_source_owner.q[0];',
 " end else assign native_bank_query_empty[i]=1'b0;",
 ' assign source_owner_native_rf_workspace_free[i]=!tc_busy[i] && !tc_fault[i] && !native_aperture_rfroute_route_fault[i] && (rfdrain_w6_local_RF_empty[i] || private_held);',
 ' wire stage_Q=source_owner_query_result_valid[i] && source_owner_source_owner_retained[i] && source_owner_query_result_workspace[i] && source_owner_query_result_write[i] && source_owner_query_result_tuple[i*239+:239]==source_owner_workspace_held_tuple[i*239+:239];',
 ' wire initial_scope=ENABLE_NATIVE_APERTURES && source_owner_issued_input_live[i] && source_owner_inputs_bound_tuple[i*239+164+:11]==11\'d2047;',
 ' wire initial_Q=source_owner_query_result_valid[i] && source_owner_source_owner_retained[i] && source_owner_query_result_write[i] && source_owner_query_result_tuple[i*239+:239]==native_initial_event_tuple && sm_host_dst[i*9+:9]==source_owner_query_result_slot[i*9+:9] && sm_host_owner[i*46+:46]==source_owner_query_result_owner[i*46+:46];',
 ' wire initial_offer_admit=!initial_scope || ((i==0 || i==32) && native_initial_initial_write_admit[(i==32)?1:0] && initial_Q);',
 ' assign native_external_write_admit[i]=initial_offer_admit && (!ENABLE_NATIVE_APERTURES || native_aperture_rfroute_bank_routes_drained[i]) && !native_aperture_rfroute_bank_wr_valid[i] && !native_aperture_rfroute_bank_rd_valid[i] && (!native_private_reservation || (stage_Q && sm_host_dst[i*9+:9]==source_owner_query_result_slot[i*9+:9] && sm_host_owner[i*46+:46]==source_owner_query_result_owner[i*46+:46]));',
 ' assign native_external_read_admit[i]=(!ENABLE_NATIVE_APERTURES || native_aperture_rfroute_bank_routes_drained[i]) && !native_aperture_rfroute_bank_wr_valid[i] && !native_aperture_rfroute_bank_rd_valid[i] && !native_private_reservation;',
 ' assign sm_host_rd_ready[i]=raw_backend_rd_ready[i] && native_external_read_admit[i];',
 ' assign sm_host_wr_ready[i]=raw_backend_wr_ready[i] && native_external_write_admit[i];',
 ' assign native_backend_rd_ready[i]=raw_backend_rd_ready[i];assign native_backend_wr_ready[i]=raw_backend_wr_ready[i];',
 'end']
 # ONE real INITIAL completion endpoint, driven by actual old RF/Q/W4 taps.
 init={};initial_ports=ports(ROOT/INITIAL)
 native_initial='native_initial_'
 for n in ['go_input_bits','close_valid','close_tuple','close_owner']:
  p=initial_ports[n];add(native_initial+n,'input',p['bits'],1,n,'native_initial',True);init[n]=native_initial+n
 for n in ['go_ready','close_ready','initial_write_admit','provider_quiesce','busy','fault','event_tuple','event_owner','visible_valid','terminal_valid','reverse_valid']:
  p=initial_ports[n];add(native_initial+n,'output',p['bits'],1,n,'native_initial',False);init[n]=native_initial+n
 extra+=['wire [63:0] accepted_initial_ready=issuer_initial_go_ready & {64{!ENABLE_NATIVE_APERTURES || native_initial_go_ready}};',
 'wire [238:0] selected_initial_tuple=issuer_initial_go_valid[0] ? issuer_initial_go_tuple[0+:239] : issuer_initial_go_tuple[32*239+:239];',
 'wire [54:0] selected_initial_owner=issuer_initial_go_valid[0] ? issuer_initial_go_owner[0+:55] : issuer_initial_go_owner[32*55+:55];',
 'wire [5:0] initial_actor=native_initial_event_tuple[35:30];',
 'wire [63:0] initial_go_accepted=issuer_initial_go_valid & accepted_initial_ready;',
 'wire [1:0] initial_bank_scope={native_initial_busy && source_owner_issued_input_live[32] && source_owner_inputs_bound_tuple[32*239+:239]==native_initial_event_tuple,native_initial_busy && source_owner_issued_input_live[0] && source_owner_inputs_bound_tuple[0+:239]==native_initial_event_tuple};',
 'wire [63:0] actual_producer_visible_valid,actual_whole_terminal_valid,actual_whole_reverse_valid;',
 'wire [15295:0] actual_producer_visible_tuple,actual_whole_terminal_tuple,actual_whole_reverse_tuple;']
 sv=once(sv,'.initial_go_ready(issuer_initial_go_ready)', '.initial_go_ready(accepted_initial_ready)')
 sv=once(sv,'(issuer_initial_go_valid & issuer_initial_go_ready)','(issuer_initial_go_valid & accepted_initial_ready)')
 for kind in ['producer_visible','whole_terminal','whole_reverse']:
  sv=once(sv,'.'+kind+'_valid(issuer_'+kind+'_valid)','. '+kind+'_valid(actual_'+kind+'_valid)'.replace('. ','.'))
  sv=once(sv,'.'+kind+'_tuple(issuer_'+kind+'_tuple)','. '+kind+'_tuple(actual_'+kind+'_tuple)'.replace('. ','.'))
 sv=once(sv,'.root_visible_tuple(issuer_producer_visible_tuple)','.root_visible_tuple(actual_producer_visible_tuple)')
 sv=once(sv,'.root_visible_valid(issuer_producer_visible_valid)','.root_visible_valid(actual_producer_visible_valid)')
 extra+=['for(genvar i=0;i<64;i=i+1)begin:actual_INITIAL_receipts',
 ' wire is_initial=ENABLE_NATIVE_APERTURES && issuer_busy[i] && issuer_publish_tuple[i*239+164+:11]==2047;',
 ' assign actual_producer_visible_valid[i]=is_initial ? native_initial_visible_valid && initial_actor==i : issuer_producer_visible_valid[i];',
 ' assign actual_whole_terminal_valid[i]=is_initial ? native_initial_terminal_valid && initial_actor==i : issuer_whole_terminal_valid[i];',
 ' assign actual_whole_reverse_valid[i]=is_initial ? native_initial_reverse_valid && initial_actor==i : issuer_whole_reverse_valid[i];',
 ' assign actual_producer_visible_tuple[i*239+:239]=is_initial ? native_initial_event_tuple : issuer_producer_visible_tuple[i*239+:239];',
 ' assign actual_whole_terminal_tuple[i*239+:239]=is_initial ? native_initial_event_tuple : issuer_whole_terminal_tuple[i*239+:239];',
 ' assign actual_whole_reverse_tuple[i*239+:239]=is_initial ? native_initial_event_tuple : issuer_whole_reverse_tuple[i*239+:239];',
 'end']
 def pair(n,w):return '{'+n+f'[32*{w}+:{w}],'+n+f'[0+:{w}]'+'}'
 init.update(clk='stream_clk',power_on_reset_n='issuer_por_n',warm_reset='(|source_owner_warm_reset)',go_valid='(|initial_go_accepted)',go_tuple='selected_initial_tuple',go_owner='selected_initial_owner',
 write_accept='('+pair('sm_rf_write_accept',1)+' & initial_bank_scope)',write_slots=pair('sm_host_dst',9),write_owners=pair('sm_host_owner',46),write_data=pair('sm_host_wdata',4096),
 query_valid=pair('source_owner_query_result_valid',1),query_owner_retained=pair('source_owner_source_owner_retained',1),query_tuples=pair('source_owner_query_result_tuple',239),query_slots=pair('source_owner_query_result_slot',9),query_owners=pair('source_owner_query_result_owner',46),
 ACK_accept='('+pair('sm_rf_ack_accept',1)+' & initial_bank_scope)',ACK_slots=pair('sm_host_ack_slot',9),ACK_owners=pair('sm_host_ack_owner',46),
 root_ACK_accept='native_initial_busy && issuer_rf_range_ack_valid[initial_actor] && issuer_rf_range_ack_ready[initial_actor]',root_ACK_tuple='issuer_rf_range_ack_tuple[initial_actor*239+:239]',root_ACK_owner='issuer_rf_range_ack_owner[initial_actor*55+:55]',
 RF_drained='{rfdrain_w6_local_RF_empty[32] && !tc_busy[32] && native_bank_query_empty[32] && native_aperture_rfroute_bank_routes_drained[32],rfdrain_w6_local_RF_empty[0] && !tc_busy[0] && native_bank_query_empty[0] && native_aperture_rfroute_bank_routes_drained[0]}',
 visible_ready='issuer_producer_visible_ready[initial_actor]',terminal_ready='issuer_whole_terminal_ready[initial_actor]',reverse_ready='issuer_whole_reverse_ready[initial_actor]',
 frame_retire_accept='native_initial_busy && issuer_frame_retire_valid[initial_actor] && issuer_frame_retire_ready[initial_actor]',frame_retire_tuple='issuer_frame_retire_tuple[initial_actor*239+:239]',frame_retire_owner='issuer_frame_retire_owner[initial_actor*55+:55]')
 extra+=['ot_gpu_qwen_initial_completion #(.ENABLE(ENABLE && ENABLE_MANIFEST && ENABLE_BANK_BARRIER && ENABLE_NATIVE_APERTURES)) u_actual_INITIAL(\n '+',\n '.join('.'+p+'('+init[p]+')' for p in initial_ports)+'\n);']
 # Preserve scratch/global-router drain and add physical primitive route/cursor
 # debt. FRAME retirement cannot erase a live micro-RPC or source lease.
 sv=once(sv,'assign source_owner_workspace_children_drained[i]=scratch_drained[i] && kv_shared_drained;',
 'assign source_owner_workspace_children_drained[i]=scratch_drained[i] && kv_shared_drained && (!ENABLE_NATIVE_APERTURES || ((&native_aperture_rfroute_bank_routes_drained) && (&native_bank_query_empty) && !(|native_aperture_context_live) && !(|native_aperture_source_cursor_valid) && !(|native_aperture_source_cursor_advance_valid)));')
 extra+=['ot_gpu_qwen_native_aperture_cluster #(.ENABLE(ENABLE && ENABLE_NATIVE_APERTURES && ENABLE_MANIFEST && ENABLE_BANK_BARRIER)) u_actual_native_apertures(\n '+',\n '.join('.'+p+'('+n+')' for p,n in links.items())+'\n);']
 sv=once(sv,'\n);\nassign assembly_enabled',',\n'+',\n'.join(decl)+'\n);\nassign assembly_enabled')
 sv=once(sv,'\nendmodule','\n'+'\n'.join(extra)+'\nendmodule')
 gets=[];sets=[]
 for n,p in new.items():
  w=p['bits'];expr=f'word(dut.{n});' if w<=32 else f'word(uint32_t(dut.{n}>>32));word(uint32_t(dut.{n}));' if w<=64 else f'for(int i={(w+31)//32-1};i>=0;i--)word(dut.{n}[i]);'
  gets.append(f' if(name=="{n}"){{{expr}}} else')
  if p['host_writable']:
   setexpr=f'dut.{n}=v[0];' if w<=32 else f'dut.{n}=uint64_t(v[0])|(uint64_t(v[1])<<32);' if w<=64 else f'for(unsigned i=0;i<v.size();i++)dut.{n}[i]=v[i];'
   sets.append(f' if(name=="{n}"){{auto v=unpack(value,{w});{setexpr}std::cout<<"OK";}} else')
 cpp=once(cpp,' throw std::runtime_error("unknown pin");}','\n'.join(gets)+'\n throw std::runtime_error("unknown pin");}')
 cpp=once(cpp,' throw std::runtime_error("unknown/output pin");}','\n'.join(sets)+'\n throw std::runtime_error("unknown/output pin");}')
 deps=(BASE/'sources.f').read_text().splitlines();oldtop=deps.pop();deps.extend([BANK,COL,ROUTE,CLUSTER,INITIAL]);top=str((out/(b['top']+'.sv')).relative_to(ROOT));deps.append(top)
 b['source_sha256'].pop(oldtop);b['source_sha256'].update({p:sha(p) for p in [BANK,COL,ROUTE,CLUSTER,INITIAL]});b['source_sha256'][top]=hashlib.sha256(sv.encode()).hexdigest();b['pins'].update(new)
 b['manifest_contract']['owner_module']='ot_gpu_qwen_native_aperture_range_owner';b['manifest_contract']['allocator_commit']='434786b2a914348953a46adc01cebda0823fc59c';b['manifest_contract']['ABI_sha256']=sha('results/uarch/canonical_qwen_native_apertures_20261003/pins.json')
 b['native_aperture_contract']=dict(collector_count=64,actual_module='ot_gpu_qwen_native_aperture_collector',route_module='ot_gpu_qwen_native_rf_route_r2',full_build_ready=False,physical_profile_and_controller_installed=False,missing='Pauli frozen shapeROM and controller_authority must drive read-only physical input boundaries before fullbuild',private_workspace='real TC/legacy RF drain then retained coded workspace capture; never tied free1',source_scope='wholePC remains banked immutable masks, private ACK slots0..9 excluded from canonical child bitmap ACK')
 b['full_build_ready']=False;b['unresolved']+=['Installed real INITIAL endpoint still requires actual joined shared-reset/source-RF/W6 context acceptance gate','Native RF W6 request context identity/key and compiled shared reset joins still require actual held root wiring']
 out.mkdir(parents=True);(out/(b['top']+'.sv')).write_text(sv);(out/'ports.json').write_text(json.dumps(b,indent=2)+'\n');(out/'sources.f').write_text('\n'.join(deps)+'\n');(out/'pin_driver.cpp').write_text(cpp)
 return out
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args();print(generate(a.out))
