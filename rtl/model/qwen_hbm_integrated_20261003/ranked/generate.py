"""Source-derived sibling of the preserved128-total enclosing assembly.

No engine leaf changes. Model must be committed before this generator is used.
The existing checked grant key retains rank; real reverse sender rank is an
independent pin and cannot be reconstructed from the expected grant.
"""
import hashlib, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
OUT=Path(__file__).resolve().parent
BASE=OUT.parent


def replace_once(text, old, new):
    if text.count(old)!=1:raise ValueError('source derivation changed: '+old[:70])
    return text.replace(old,new)


# Exact source pin joins. No owner, ready, ACK or debt is synthesized here.
RPC_TAP={n:n[4:] for n in ('tap_command_valid','tap_command_ready','tap_command_rank','tap_command_write','tap_command_sector_granted','tap_command_identity','tap_command_source_addr','tap_command_physical_addr','tap_command_owner','tap_command_new_data','tap_command_byte_mask','tap_reply_valid','tap_reply_ready','tap_reply_identity','tap_reply_rank','tap_reply_owner','tap_reply_physical_addr','tap_reply_old_data')}

RF_FROM_SM={n:n for n in ('rf_write_accept','rf_write_owner55','rf_ack_valid','rf_ack_accept','rf_ack_owner55','rf_ack_fault','rf_read_accept','rf_read_a','rf_read_b','rf_rsp_valid','rf_rsp_accept','simd_context_accept','simd_context_owner55','simd_context_retire','simd_retire_owner55','wr_continuation_valid','wr_continuation_source','rd_continuation_valid','rd_continuation_source','rd_context_owner55')}
RF_FROM_SM.update({n:'wr_context_'+n[3:] for n in ('wr_binding_valid','wr_KV_related','wr_identity','wr_key')})
RF_FROM_SM.update({n:'rd_context_'+n[3:] for n in ('rd_binding_valid','rd_KV_related','rd_identity','rd_key')})
RF_FROM_SM.update(simd_binding_valid='simd_binding_valid',simd_KV_related='simd_KV_related',simd_identity='simd_source_identity',simd_key='simd_key',source_fault='identity_fault')
SM_FROM_RF={n:n for n in ('simd_context_permit','rd_permit','wr_permit','rf_rsp_allow','rf_ack_allow')}
STATE_SELECTED=dict(caller_req_v='c_req_v',caller_req_we='c_req_we',caller_req_addr='c_req_addr',caller_req_tag='c_req_tag',caller_req_gen='c_req_gen',caller_req_data='c_req_data',caller_rsp_rdy='c_rsp_rdy',caller_wr_done_rdy='c_wr_done_rdy',raw_rsp_v='c_rsp_v',raw_wr_done_v='c_wr_done_v',raw_rsp_tag='c_rsp_tag',raw_wr_done_tag='c_wr_done_tag',raw_rsp_gen='c_rsp_gen',raw_wr_done_gen='c_wr_done_gen',raw_rsp_data='c_rsp_data')
OBSERVER={n:n for n in ('observe_valid','observe_ready','observe_rank','observe_source_addr','observe_physical_addr','observe_owner','observe_old_data','observe_new_data','observe_old_captured','ACK_valid','ACK_ready','ACK_owner','ACK_physical_addr','ACK_visible','ACK_reverse')}


def join_pin(pins,prefix,name,expression):
    target=prefix+'_'+name
    # Retain joined pins for observation; make driveninput a readonlyoutput.
    if target in pins and pins[target]['direction']=='input':
        pins[target]['direction']='output'
        JOINED_ALIASES[target]=expression
    return expression


JOINED_ALIASES={}
def installed_connection(prefix,name,bits,count,pins,expression):
    if prefix=='kv' and name in ('cohort_req_ready','cohort_rsp_valid','cohort_rsp_empty'):
        signal={'cohort_req_ready':'local_request_ready','cohort_rsp_valid':'local_response_valid','cohort_rsp_empty':'local_response_quiet'}[name]
        rf={'cohort_req_ready':'rfcohort_req_ready','cohort_rsp_valid':'rfcohort_rsp_valid','cohort_rsp_empty':'rfcohort_rsp_empty'}[name]
        return "(kv_%s & 8'hE6) | ({8{%s}} & 8'h10) | {4'b0,%s[1],2'b0,%s[0]}" % (name,rf,signal,signal)
    if prefix=='kv' and name=='cohort_rsp_tuple':return '{kv_cohort_rsp_tuple[671:420],rfcohort_rsp_tuple,local_response_key[39:20],local_response_identity[127:64],kv_cohort_rsp_tuple[251:84],local_response_key[19:0],local_response_identity[63:0]}'
    if prefix=='state_rpc' and name in RPC_TAP:
        if name=='tap_command_ready':return join_pin(pins,prefix,name,'state_command_ready')
        if name.startswith('tap_reply_') and name!='tap_reply_ready':return join_pin(pins,prefix,name,'state_'+RPC_TAP[name])
    if prefix=='state' and ('tap_'+name) in RPC_TAP:
        if name=='command_valid':return join_pin(pins,prefix,name,'state_rpc_tap_command_valid && (!sector_grant_live || state_route_shared)')
        if name=='command_ready':return 'raw_state_command_ready'
        if name.startswith('command_') or name=='reply_ready':return join_pin(pins,prefix,name,'state_rpc_tap_'+name)
    if prefix=='state_rpc' and name in ('root_admit','root_retire_ready'):return join_pin(pins,prefix,name,'local_state_'+name)
    local_sources={'state_root_accept':'state_rpc_root_accept','state_root_retire':'state_rpc_root_retire','state_root_identity':'state_rpc_root_identity','state_root_retire_identity':'state_rpc_root_retire_identity','shared_router_drained':'kv_shared_drained','writer_retained':'kv_writer_retained','shared_service_ready':'sm_scratch_ready','shared_service_done':'sm_scratch_done','state_tap_quiescent':'state_quiescent','state_observer_drained':'kv_state_observer_drained','metadata_ACK_held':'kv_ACK_valid','metadata_reverse_held':'state_ACK_reverse','metadata_event_held':'kv.c_metadata_valid || kv.c_reader_metadata_valid || kv.event_valid','request_valid':"{kv_cohort_req_valid[3],kv_cohort_req_valid[0]}",'request_identity':'kv_cohort_identity','request_key':'kv_cohort_key','response_ready':"{kv_cohort_rsp_ready[3],kv_cohort_rsp_ready[0]}"}
    if prefix=='local' and name in local_sources:return join_pin(pins,prefix,name,local_sources[name])
    if prefix=='kv' and name=='endpoint_fault':return 'kv_endpoint_fault || (|rfdrain_fault) || (|rfjoin_fault) || rfcohort_tuple_mismatch || state_fault || (|issuer_fault) || issuer_session_fault || local_fault || state_rpc_fault'
    if prefix=='rfjoin' and name=='drain_req_valid':return join_pin(pins,prefix,name,'kv_cohort_req_valid[4] && rfcohort_req_ready')
    if prefix=='rfjoin' and name=='drain_req_identity':return join_pin(pins,prefix,name,'kv_cohort_identity')
    if prefix=='rfjoin' and name=='drain_req_key':return join_pin(pins,prefix,name,'kv_cohort_key')
    if prefix=='rfjoin' and name=='drain_hold':return join_pin(pins,prefix,name,'kv_drain_retained')
    if prefix=='rfjoin' and name=='drain_rsp_ready':return join_pin(pins,prefix,name,'kv_cohort_rsp_ready[4] && rfcohort_rsp_valid')
    if prefix=='rfdrain' and name in RF_FROM_SM:
        target=RF_FROM_SM[name];value='sm_'+target+(f'[i*{bits} +: {bits}]' if bits>1 else '[i]')
        return join_pin(pins,prefix,name,value)
    if prefix=='sm' and name in SM_FROM_RF:
        return join_pin(pins,prefix,name,'rfdrain_'+name+'[i]')
    if prefix=='state' and name=='command_valid':raise ValueError('RPC command must use installed join')
    if prefix=='state' and name=='command_ready':return 'raw_state_command_ready'
    if prefix=='sector' and name in ('caller_req_v','caller_rsp_rdy','caller_wr_done_rdy'):
        permit='state_req_permit' if name=='caller_req_v' else 'state_capture_permit'
        return f'(w2_{STATE_SELECTED[name]}[selected_index*6 +: 6] & (state_route_shared ? {permit} : 6\'b111111))'
    if prefix=='state' and name in ('caller_req_v','caller_rsp_rdy','caller_wr_done_rdy'):
        permit='sector_req_permit' if name=='caller_req_v' else 'sector_capture_permit'
        return join_pin(pins,prefix,name,f'(w2_{STATE_SELECTED[name]}[selected_index*6 +: 6] & (state_route_shared ? {permit} : 6\'b111111))')
    if prefix=='state' and name in STATE_SELECTED:
        return join_pin(pins,prefix,name,f'w2_{STATE_SELECTED[name]}[selected_index*{bits} +: {bits}]')
    if prefix=='state' and name=='raw_req_rdy':return join_pin(pins,prefix,name,'raw_w2_req_rdy[selected_index*6 +: 6]')
    if prefix=='state' and name=='bus_rank':return join_pin(pins,prefix,name,'selected_index[7]')
    if prefix=='state' and name=='bus_PC':return join_pin(pins,prefix,name,'selected_PC')
    if prefix=='state' and name=='reverse_valid':return join_pin(pins,prefix,name,'sector_reverse_valid && state_bus_owned && (!state_route_shared || payload_reverse_ready)')
    if prefix=='state' and name=='reverse_rank':return join_pin(pins,prefix,name,'sector_reverse_rank')
    if prefix=='state' and name=='reverse_write':return join_pin(pins,prefix,name,'sector_reverse_write')
    if prefix=='state' and name=='reverse_owner':return join_pin(pins,prefix,name,'sector_reverse_route[45:0]')
    if prefix=='state' and name=='reverse_physical_addr':return join_pin(pins,prefix,name,'sector_reverse_route[79:46]')
    if prefix=='state' and name=='W2_fault':return join_pin(pins,prefix,name,'w2_fault[selected_index]')
    if prefix=='state' and name=='repair_busy':return join_pin(pins,prefix,name,'w2_repair_busy[selected_index]')
    if prefix=='kv' and name in OBSERVER and name not in ('observe_ready','ACK_ready'):
        return join_pin(pins,prefix,name,'state_'+name)
    if prefix=='state' and name in ('observe_ready','ACK_ready'):
        return join_pin(pins,prefix,name,'kv_'+name)
    if prefix=='rfdrain' and name in ('drain_req_valid','drain_rsp_ready','drain_hold'):
        leaf={'drain_req_valid':'leaf_req_valid','drain_rsp_ready':'leaf_rsp_ready','drain_hold':'leaf_hold'}[name]
        return join_pin(pins,prefix,name,'rfjoin_'+leaf+'[i]')
    if prefix=='rfdrain' and name in ('drain_req_identity','drain_req_key'):
        leaf={'drain_req_identity':'leaf_identity','drain_req_key':'leaf_key'}[name]
        return join_pin(pins,prefix,name,f'rfjoin_{leaf}[(i/32)*{bits} +: {bits}]')
    if prefix=='rfjoin' and name in ('leaf_req_ready','leaf_rsp_valid','leaf_rsp_empty','leaf_fault'):
        leaf={'leaf_req_ready':'drain_req_ready','leaf_rsp_valid':'drain_rsp_valid','leaf_rsp_empty':'drain_rsp_empty','leaf_fault':'fault'}[name]
        return join_pin(pins,prefix,name,'rfdrain_'+leaf+'[i*32 +: 32]')
    if prefix=='rfjoin' and name=='leaf_rsp_tuple':return join_pin(pins,prefix,name,'rfdrain_response_tuple[i*2688 +: 2688]')
    return expression

def main():
    model=json.loads((OUT/'model.json').read_text())
    source=BASE/'generate.py'
    expected=model['source_sha256'][str(source.relative_to(ROOT))]
    if hashlib.sha256(source.read_bytes()).hexdigest()!=expected:raise ValueError('priced source changed')
    # Preserve all source-selected leaves/ports/clock. Reuse generator machinery
    # in a sibling output directory and bind each transform to exact old source.
    issuer_model=json.loads((BASE/'issuer/r2/model.json').read_text())
    if issuer_model['tuple_bits']!=239 or issuer_model['inventory']['coded_FF_bits']!=37008:
        raise ValueError('priced issuer dimensions differ')
    text=source.read_text()
    text=replace_once(text, "BLOCKS = (", "BLOCKS = (\n ('state_rpc', 'rtl/model/qwen_kv_connections_20261003/ot_gpu_qwen_kv_state_rpc_join.sv', 'ot_gpu_qwen_kv_state_rpc_join', 1, '.ENABLE(ENABLE)'),\n ('local', 'rtl/model/qwen_kv_connections_20261003/ot_gpu_qwen_kv_local_cohorts_terminal_ready.sv', 'ot_gpu_qwen_kv_local_cohorts_terminal_ready', 1, '.ENABLE(ENABLE)'),\n ('issuer', 'rtl/model/qwen_hbm_integrated_20261003/issuer/r2/ot_gpu_qwen_full_issuer_r2.sv', 'ot_gpu_qwen_full_issuer_r2', 1, '.ENABLE(ENABLE)'),\n ('state', 'rtl/model/qwen_kv_connections_20261003/ot_gpu_qwen_kv_state_w2_tap.sv', 'ot_gpu_qwen_kv_state_w2_tap', 1, '.ENABLE(ENABLE)'),\n ('rfdrain', 'rtl/model/qwen_rf_ack_drain_20261003/r2/ot_gpu_qwen_rf_ack_drain_r2.sv', 'ot_gpu_qwen_rf_ack_drain_r2', 64, '.ENABLE(ENABLE)'),\n ('rfjoin', 'rtl/model/qwen_rf_ack_drain_20261003/ot_gpu_qwen_rf_ack_drain_join.sv', 'ot_gpu_qwen_rf_ack_drain_join', 2, '.ENABLE(ENABLE)'),")
    text=replace_once(text,'ROOT = Path(__file__).resolve().parents[3]','ROOT = Path(__file__).resolve().parents[4]')
    text=replace_once(text,"128, '.OPT_EXACT(ENABLE),.OPT_RESET_QUARANTINE(ENABLE),.PC_ID(7\\'(i))'", "256, '.OPT_EXACT(ENABLE),.OPT_RESET_QUARANTINE(ENABLE),.PC_ID(7\\'(i%128))'")
    text=text.replace("('sm', W4+'ot_gpu_full_sm_service.sv', 'ot_gpu_full_sm_service', 64, '.ENABLE(ENABLE),.ACK_ID(1)')","('sm', 'rtl/model/qwen_hbm_integrated_20261003/guarded_sm/ot_gpu_full_sm_service_guarded.sv', 'ot_gpu_full_sm_service_guarded', 64, '.ENABLE(ENABLE),.ACK_ID(1),.OPT_CONTEXT(ENABLE),.INSTANCE_ID(i)')")
    text=replace_once(text,'    joined_kv()','    # Reuse unchanged joined controller source; never generate a second controller.')
    text=replace_once(text,'    instances = []', '''    pins.update({
      'sector_map_rank':dict(direction='input',bits=1,count=1,leaf='map_rank',block='sector'),
      'sector_reverse_rank':dict(direction='input',bits=1,count=1,leaf='reverse_rank',block='sector'),
      'sector_rank_refusal':dict(direction='output',bits=1,count=1,leaf='rank_refusal',block='sector')})
    instances = []''')
    text=replace_once(text, "            if prefix=='kv' and name in shared:", '''            if prefix=='sector' and name in ('alloc_valid','map_valid'):
                expression='rank_checked_'+name+' && !state_bus_owned'
            elif prefix=='sector' and name=='alloc_ready':
                expression='rank_raw_alloc_ready'
            elif prefix=='sector' and name=='reverse_valid':
                expression='rank_checked_reverse_valid'
            elif prefix=='sector' and name=='reverse_ready':
                expression='rank_raw_reverse_ready'
            if prefix=='kv' and name in shared:''')
    text=replace_once(text,"            connection.append(f'.{name}({expression})')",
      """            expression=installed_connection(prefix,name,bits,count,pins,expression)
            connection.append(f'.{name}({expression})')""")
    text=text.replace('selected_PC*{bits}','selected_index*{bits}')
    text=text.replace('raw_w2_req_rdy[selected_PC*6','raw_w2_req_rdy[selected_index*6')
    text=replace_once(text,'wire [6:0] selected_PC = sector_grant_live ? sector_grant_identity[45:39] : sector_map_PC;','wire [6:0] selected_PC;')
    text=replace_once(text,'wire [767:0] raw_w2_req_rdy', """wire state_route_shared=sector_grant_live &&
 sector_grant_identity[136]==(state_quiescent ? state_command_rank : state_reply_rank) &&
 sector_grant_identity[79:46]==(state_quiescent ? state_command_physical_addr : state_reply_physical_addr) &&
 sector_grant_identity[45:0]==(state_quiescent ? state_command_owner : state_reply_owner);
wire state_bus_owned=!state_quiescent || (state_command_valid && state_command_sector_granted && (!sector_grant_live || state_route_shared));
wire [6:0] payload_selected_PC;
wire [7:0] payload_selected_index;
wire [7:0] selected_index=state_bus_owned ?
 (state_quiescent ? {state_command_rank,state_command_owner[45:39]} : {state_reply_rank,state_reply_owner[45:39]}) : payload_selected_index;
assign selected_PC=selected_index[6:0];
wire payload_alloc_ready,payload_reverse_ready,raw_state_command_ready;
assign state_command_ready=raw_state_command_ready && (!sector_grant_live || state_route_shared);
assign sector_alloc_ready=payload_alloc_ready && !state_bus_owned;
assign sector_reverse_ready=state_bus_owned ? (state_reverse_ready && (!state_route_shared || payload_reverse_ready)) : payload_reverse_ready;
wire rank_raw_alloc_ready,rank_raw_reverse_ready;
wire rank_checked_alloc_valid,rank_checked_map_valid,rank_checked_reverse_valid;
ot_gpu_qwen_rank_boundary #(.ENABLE(ENABLE)) rank_boundary(
 .grant_live(sector_grant_live),.grant_identity(sector_grant_identity),
 .alloc_valid(sector_alloc_valid),.map_valid(sector_map_valid),.map_rank(sector_map_rank),
 .alloc_source(sector_alloc_source),.map_PC(sector_map_PC),.raw_alloc_ready(rank_raw_alloc_ready),
 .reverse_valid(sector_reverse_valid && (!state_bus_owned || (state_route_shared && state_reverse_ready))),.reverse_rank(sector_reverse_rank),.raw_reverse_ready(rank_raw_reverse_ready),
 .alloc_valid_checked(rank_checked_alloc_valid),.map_valid_checked(rank_checked_map_valid),.alloc_ready(payload_alloc_ready),
 .reverse_valid_checked(rank_checked_reverse_valid),.reverse_ready(payload_reverse_ready),
 .selected_PC(payload_selected_PC),.selected_index(payload_selected_index),.rank_refusal(sector_rank_refusal));
wire [1535:0] raw_w2_req_rdy""")
    text=replace_once(text,'p<128','p<256')
    text=text.replace('selected_PC==p','selected_index==p')
    text=replace_once(text,"sector_req_permit : 6'b111111","(state_bus_owned ? (state_req_permit & (state_route_shared ? sector_req_permit : 6\'b111111)) : sector_req_permit) : 6'b111111")
    text=replace_once(text,"sector_capture_permit : 6'b111111","(state_bus_owned ? (state_capture_permit & (state_route_shared ? sector_capture_permit : 6\'b111111)) : sector_capture_permit) : 6'b111111")
    text=text.replace('ot_gpu_qwen_hbm_integrated', 'ot_gpu_qwen_hbm_integrated_ranked')
    # The dependency list must select sibling top, not a nonexistent old-path renamed file.
    text=text.replace('rtl/model/qwen_hbm_integrated_20261003/ot_gpu_qwen_hbm_integrated_ranked.sv',
                      'rtl/model/qwen_hbm_integrated_20261003/ranked/ot_gpu_qwen_hbm_integrated_ranked.sv')
    text=text.replace('W2_PC_count=128','W2_PC_per_rank=128, W2_total=256')
    text=text.replace('SM=64 W2=128','SM=64 W2=256 RANKS=2 PC_PER_RANK=128')
    ns={'__file__':str(OUT/'generate.py'),'__name__':'ranked_source_derivation','installed_connection':installed_connection}
    exec(compile(text,str(source),'exec'),ns)
    ns['main']()
    top=OUT/'ot_gpu_qwen_hbm_integrated_ranked.sv'
    sv=top.read_text()
    start=sv.index('for(genvar i=0;i<256;i=i+1) begin:g_w2')
    bank=sv[start:]
    bank=replace_once(bank,'for(genvar i=0;i<256;i=i+1) begin:g_w2',
      'for(genvar rank=0;rank<2;rank=rank+1) begin:g_rank\n for(genvar i=0;i<128;i=i+1) begin:g_w2')
    bank=bank.replace(".PC_ID(7'(i%128))", ".PC_ID(7'(i))")
    bank=bank.replace('[i*','[(rank*128+i)*').replace('[i]','[rank*128+i]')
    bank=replace_once(bank,' end\nendmodule',' end\nend\nendmodule')
    sv=sv[:start]+bank
    for target,expression in JOINED_ALIASES.items():
        # Instanceindex i must be unpacked at top scope for observation aliases.
        if '[i' in expression:
            width=json.loads((OUT/'ports.json').read_text())['pins'][target].get('leaf_bits',1)
            count=json.loads((OUT/'ports.json').read_text())['pins'][target]['count']
            parts=[expression.replace('[i]',f'[{k}]').replace('[i*',f'[{k}*').replace('[(i/32)*',f'[({k}/32)*') for k in reversed(range(count))]
            expression='{'+','.join(parts)+'}'
        elif '[(i/32)' in expression:
            width=json.loads((OUT/'ports.json').read_text())['pins'][target].get('leaf_bits',1)
            count=json.loads((OUT/'ports.json').read_text())['pins'][target]['count']
            expression='{'+','.join(expression.replace('[(i/32)',f'[({k}/32)') for k in reversed(range(count)))+'}'
        elif json.loads((OUT/'ports.json').read_text())['pins'][target]['count']>1:
            count=json.loads((OUT/'ports.json').read_text())['pins'][target]['count']
            expression='{'+str(count)+'{'+expression+'}}'
        sv=sv.replace('endmodule',f'assign {target}={expression};\nendmodule',1)
    rfcohort='wire rfcohort_req_ready=&rfjoin_drain_req_ready;\nwire rfcohort_tuple_mismatch=(&rfjoin_drain_rsp_valid) && ((rfjoin_drain_rsp_identity[63:0]!=rfjoin_drain_rsp_identity[127:64]) || (rfjoin_drain_rsp_key[19:0]!=rfjoin_drain_rsp_key[39:20]));\nwire rfcohort_rsp_valid=(&rfjoin_drain_rsp_valid) && (&rfjoin_drain_rsp_empty) && !rfcohort_tuple_mismatch && !(|rfjoin_fault);\nwire rfcohort_rsp_empty=rfcohort_rsp_valid;\nwire [83:0] rfcohort_rsp_tuple={rfjoin_drain_rsp_key[19:0],rfjoin_drain_rsp_identity[63:0]};\n'
    sv=sv.replace('endmodule',rfcohort+'endmodule',1)
    extra='wire [5375:0] rfdrain_response_tuple;\nfor(genvar q=0;q<64;q=q+1)begin:g_rfresponse\n assign rfdrain_response_tuple[q*84+:84]={rfdrain_drain_rsp_key[q*20+:20],rfdrain_drain_rsp_identity[q*64+:64]};\nend\n'
    sv=sv.replace('endmodule',extra+'endmodule',1)

    top.write_text(sv)
    deps=(OUT/'sources.f').read_text().splitlines()
    guard='rtl/model/qwen_hbm_integrated_20261003/ranked/ot_gpu_qwen_rank_boundary.sv'
    deps.insert(len(deps)-1,guard)
    issuer='rtl/model/qwen_hbm_integrated_20261003/issuer/r2/ot_gpu_qwen_full_issuer_r2.sv'
    old_issuer='rtl/model/qwen_hbm_integrated_20261003/issuer/ot_gpu_qwen_full_issuer.sv'
    deps.insert(len(deps)-1,old_issuer)
    deps.insert(len(deps)-1,issuer)
    installed=['rtl/model/qwen_hbm_integrated_20261003/guarded_sm/ot_gpu_full_sm_service_guarded.sv','rtl/model/qwen_rf_ack_drain_20261003/r2/ot_gpu_qwen_rf_ack_drain_r2.sv','rtl/model/qwen_rf_ack_drain_20261003/ot_gpu_qwen_rf_ack_drain_join.sv','rtl/model/qwen_kv_connections_20261003/ot_gpu_qwen_kv_state_w2_tap.sv','rtl/model/qwen_kv_connections_20261003/ot_gpu_qwen_kv_state_rpc_join.sv','rtl/model/qwen_kv_connections_20261003/ot_gpu_qwen_kv_local_cohorts_terminal_ready.sv']
    for dep in installed:deps.insert(len(deps)-1,dep)
    (OUT/'sources.f').write_text('\n'.join(deps)+'\n')
    book=json.loads((OUT/'ports.json').read_text())
    for dep in installed:book['source_sha256'][dep]=hashlib.sha256((ROOT/dep).read_bytes()).hexdigest()
    book['source_sha256'][old_issuer]=hashlib.sha256((ROOT/old_issuer).read_bytes()).hexdigest()
    book['source_sha256'][issuer]=hashlib.sha256((ROOT/issuer).read_bytes()).hexdigest()
    book['issuer_model_sha256']=hashlib.sha256((BASE/'issuer/r2/model.json').read_bytes()).hexdigest()
    book['inventory'].update(full_source_issuer_count=1,guarded_SM_count=64,RF_cohort_leaf_count=64,RF_rank_join_count=2,STATE_W2_tap_count=1,STATE_RPC_count=1,local_cohort_count=2)
    book['installed_cohorts']={'RF_ACK':4,'local_stage':0,'metadata_RPC':3}
    book['overridden_external_input_masks']={'kv_cohort_req_ready':25,'kv_cohort_rsp_valid':25,'kv_cohort_rsp_empty':25,'kv_cohort_rsp_tuple':{'cohort_indices':[0,3,4],'width_per_cohort':84}}
    book['factory_source_sha256']={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in ('tools/gpu_sys/canonical_qwen_state_rpc_join.py','tools/gpu_sys/canonical_qwen_ranked_simulator.py')}
    book['unresolved']+=['Nash actual STATE sector map/grant/source association must drive state_rpc.map_*; no static map or capture-valid readiness','Native whole scratch-command acceptance/terminal heldowner55 must drive local.stage_root_* and honor NEW root_admit; individual scratch children are not roots','Nash saved inputrows/allpageACK aggregate and Claude wholeengine actual terminal/reverse/visibility remain mandatory, no PC40 fragment equivalence']
    book['unresolved']+=issuer_model['pending']
    book['source_sha256'][guard]=hashlib.sha256((ROOT/guard).read_bytes()).hexdigest()
    p=str(top.relative_to(ROOT));book['source_sha256'][p]=hashlib.sha256(top.read_bytes()).hexdigest()
    book['derivation_inputs_sha256'][str(source.relative_to(ROOT))]=expected
    book['rank_contract']={'grant_rank_bit':136,'alloc_source_rank_bit':56,
        'inner_PC_bits':7,'bank_select':'rank*128+PC','reverse_sender_rank':'sector_reverse_rank',
        'outer_reverse_bits':81,'rank_refusal':'combinational, no ownership or release credit'}
    book['rank_model_sha256']=hashlib.sha256((OUT/'model.json').read_bytes()).hexdigest()
    book['unresolved'].append('physical outer rank mux/load/RC and real sender rank retained across reverse CDC')
    (OUT/'ports.json').write_text(json.dumps(book,indent=2)+'\n')


if __name__=='__main__':main()
