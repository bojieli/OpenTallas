#!/usr/bin/env python3
"""Compile complete HBM macro graphs to version/residence/transaction IR.
No tensor evaluation, payload readers, HDL generation or hardware timing oracle.
"""
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
import math
import re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE='4d7933caef35bd73794d9d945298cd1c0c585d16'
GEOMETRY={'ranks':{'Qwen':2,'DeepSeek':96},'SM_per_rank':32,'lanes':128,
 'RF_vectors_per_SM':512,'RF_vector_bytes':512,'RF_copies':2,'kernel_workspace_RF_vectors':32,'kernel_workspace_shared_bytes':8192,'shared_bytes_per_SM':65536,
 'shared_beat_bytes':64,'matrix_capture_bytes':{'Qwen':262144,'DeepSeek':131072}}
PINS=['tools/qwen_hbm_complete_program.py','tools/qwen_hbm_complete_executor.py',
 'tools/w19_hbm_tp96_isa.py','tools/deepseek_hbm_complete_program.py',
 'tools/deepseek_hbm_complete_executor.py','tools/deepseek_hbm_complete_isa.py',
 'tools/w19_gpu_norm_calendar.py','tools/uarch_model.py',
 'compiler/models/qwen3-8b/config.json','compiler/models/qwen3-8b/checkpoint_source.json',
 'compiler/models/deepseek-v4.1-flash/inference_config.json',
 'results/rtl/w19_hbm_tp96_program_oreduce.json','rtl/gpu/ot_gpu_full_sm_service.sv',
 'rtl/gpu/ot_gpu_rf_service.sv','rtl/gpu/ot_gpu_scratch_service.sv',
 'rtl/gpu/ot_gpu_sm_q.sv','rtl/gpu/ot_gpu_sm_v.sv','rtl/gpu/ot_gpu_xstore.sv']

def ceil(n,d):return (n+d-1)//d

def align(n,d=512):return ceil(n,d)*d

class Builder:
    def __init__(self,target):
        self.target=target;self.ranks=GEOMETRY['ranks'][target]
        self.current={};self.values=[];self.byid={};self.operations=[];self.external=[]
    def value(self,name,counts,bits=32,pc=-1,partial=None,external=False):
        if len(counts)!=self.ranks:raise ValueError('rank geometry')
        v={'id':f'{self.target}.{pc}.{name}.{len(self.values)}','name':name,'birth_pc':pc,
           'elements_per_rank':counts,'bits_per_element':bits,'producer_extent':partial,
           'consumers':[],'external_source':external,'homes':[]}
        self.values.append(v);self.byid[v['id']]=v;self.current[name]=v['id']
        if external:self.external.append(v['id'])
        return v['id']
    def read(self,name,pc):
        if name not in self.current:raise ValueError(f'undefined {self.target} operand pc{pc}: {name}')
        i=self.current[name];self.byid[i]['consumers'].append(pc);return i
    def op(self,opcode,reads,writes,pc,source,participants=None,endpoints=(),contract=None):
        ri=[self.read(n,pc) for n in dict.fromkeys(reads)];wi=[]
        for n,counts,bits,extent in writes:
            wi.append(self.value(n,counts,bits,pc,extent))
        self.operations.append({'pc':pc,'opcode':opcode,'source':source,
          'participants':list(range(self.ranks)) if participants is None else participants,
          'reads':ri,'writes':wi,'dependencies':sorted(set([pc-1] if pc else [])|{self.byid[v]['birth_pc'] for v in ri if self.byid[v]['birth_pc']>=0}),
          'golden_contract':contract,'missing_native_endpoints':sorted(set(endpoints)),
          'native_lowering':None,'timeline':{'begin_after':'TOKEN_START' if pc==0 else f'PC{pc-1}.retire',
           'retire_after':['output_commit_ACK','all_input_consumer_done'],'duration_term':f'T_{self.target}_{pc}'}})


def qwen():
    spec=importlib.util.spec_from_file_location('qwen_graph',ROOT/'tools/qwen_hbm_complete_program.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);p=m.compile_program()
    b=Builder('Qwen');b.value('token',[1]*2,pc=-1,external=True);b.value('position',[1]*2,pc=-1,external=True)
    def count(shape):return math.prod(p['context_capacity'] if x=='position+1' else x for x in shape) if shape else 1
    endpoints={'EMBED':['HBM_embedding_decode_to_RF'],'RSTD':['ordered_chunk8_tree','INT_bit_seed','cross_SM_scalar_broadcast'],
     'HEAD_NORM':['ordered_chunk8_tree','INT_bit_seed','gamma_provider','cross_SM_scalar_broadcast'],
     'FINAL_NORM':['ordered_chunk8_tree','INT_bit_seed','gamma_provider','cross_SM_scalar_broadcast'],
     'ROPE':['constant_table_to_RF','sign_bit_XOR'], 'KV_WRITE':['FP8_quantizer','selected_owner_write_visible'],
     'KV_FENCE':['selected_owner_write_visible','publication_generation'],
     'KV_READ':['published_KV_decode_to_RF','reader_retirement'],
     'SCORES':['interleaved_head_tree','KV_tile_loader'], 'PV':['interleaved_context_tree','KV_tile_loader'],
     'EXP_SUM':['ordered_max_tree','EXP_poly_INT_compare','ordered_chunk8_tree','BF16_round_pack'],
     'NORMALIZE':['reciprocal_division','scalar_lane_broadcast'],
     'ALL_REDUCE':['rank2_ordered_FP32_add_route','post_reduce_scale_provider'],
     'SILU_GATE':['EXP_poly_INT_compare','reciprocal_division','split_gate_up_lane_route'],
     'ARGMAX':['compare_global_ID_tie','ordered_max_tree'], 'ARGMAX_REDUCE':['rank2_winner_route'],
     'QKV_SPLIT':['view_lane_remap'], 'ROW_SCALE':['row_scale_to_RF'], 'SCALAR_MUL':['scalar_lane_broadcast'],
     'RESIDUAL':[], 'MATRIX':['HBM_weight_stream','matrix_xstore_loader','addressed_capture_to_RF']}
    for o in p['instructions']:
        writes=[]
        for n in o['outputs']:
            participants=o['participants'];counts=[count(p['register_shapes'][n]) if r in participants else 0 for r in range(2)]
            # Publication objects are opaque source identities, not numeric words.
            bits=0 if o['opcode'] in ('KV_WRITE','KV_FENCE') else 64 if o['opcode']=='ARGMAX' else 32
            writes.append((n,counts,bits,None))
        contract=m.OPCODES[o['opcode']]
        b.op(o['opcode'],o['inputs'],writes,o['id'],{'path':'tools/qwen_hbm_complete_program.py','attributes':o['attributes']},
             o['participants'],endpoints[o['opcode']],contract)
        b.operations[-1]['external_bindings']={'immutable_weight_descriptor':p['weight_descriptors'].get(o['attributes'].get('weight',o['attributes'].get('post_scale_weight'))), 'checkpoint_constant':o['attributes'].get('checkpoint'), 'norm_gamma':{'layer':o['attributes'].get('layer'),'kind':o['attributes'].get('kind')} if o['opcode'] in ('HEAD_NORM','FINAL_NORM') else None,'actual_provider_port':None}
        b.operations[-1]['recipe']=o['GPU_instructions'] if 'GPU_instructions' in o else p.get('lowering_instructions',{}).get(o['opcode'])
    return b,p


def ds():
    cfg=json.loads((ROOT/'compiler/models/deepseek-v4.1-flash/inference_config.json').read_text())
    g=json.loads((ROOT/'results/rtl/w19_hbm_tp96_program_oreduce.json').read_text());b=Builder('DeepSeek')
    def rep(n,ranks=None):return [n if ranks is None or r in ranks else 0 for r in range(96)]
    def owned(n):return [(n//768)*8+min(8,max(0,n%768-r*8)) for r in range(96)]
    def part(n):return [n*(r+1)//96-n*r//96 for r in range(96)]
    b.value('h',rep(20480),external=True);b.value('pre',rep(4),external=True)
    # Persistent histories/state are actual external producer obligations; no anonymous preload.
    for l in range(40):b.value(f'window.L{l}',rep(128*512),external=True)
    for src in cfg['kv_source_layers']:b.value(f'compressed.L{src}',[v*512 for v in owned(g['position']//cfg['compress_ratios'][src])],external=True)
    for src in cfg['kv_source_layers']:b.value(f'index_keys.L{src}',[v*128 for v in owned(g['position']//cfg['compress_ratios'][src])],external=True)
    pc=0
    for layer in g['layers']:
      # Actual complete executor clears transient rank.mem at layer boundaries.
      b.current={n:v for n,v in b.current.items() if n in ('h','pre','sel','candidate_keep') or n.startswith(('window.','compressed.','index_keys.','selected.'))}
      for o in layer['ops']:
        k=o['kind'];fn=o.get('fn',k);rs=list(range(96)) if o.get('ranks','all')=='all' else list(range(64)) if o.get('ranks')=='heads' else o['ranks']
        reads=[];w=[];missing=[];contract='source handler '+fn
        def put(n,c,bits=32,ext=None):w.append((n,c,bits,ext))
        def read(*names):reads.extend(names)
        if k=='mv':
            read('o_own' if fn=='wo_a_part' else o['x']);put(o['out'],[hi-lo for lo,hi in o['rows']],32,o['rows'])
            missing=['HBM_weight_stream','matrix_xstore_loader','addressed_capture_to_RF']
            contract='contiguous whole-K per output row; source '+fn+' chunk8/tree/quantized round points'
        elif k=='all_gather':
            for n in o['bufs']:
                read(n);v=b.byid[b.current[n]];extent=v['producer_extent'];full=max(hi for lo,hi in extent) if isinstance(extent,list) else extent['full_extent'] if isinstance(extent,dict) and 'full_extent' in extent else o['elems'] if len(o['bufs'])==1 else sum(v['elements_per_rank']);put(n,rep(full,list(range(96)) if o['dest']=='all' else list(range(64))),v['bits_per_element'])
            if o['tag']=='expert_intermediate_gather':
                for e in range(7):put(f'ea{e}',rep(2304))
            missing=['rank96_gather_route','gather_owned_extent_certificate']
        elif k=='all_reduce':
            read(o['buf']);put(o['out'],rep(o['elems']));missing=['rank8_pairwise_reduce_route','BF16_round_pack']
            contract='8 ranks per group fixed ((0+1)+(2+3))+((4+5)+(6+7)); BF16 after tree'
        elif k=='topk_merge':
            n=o['what'];read(n+'_v',n+'_i');missing=['rank96_ordered_topk_route','compare_global_ID_tie']
            if n=='argmax':put('token',rep(1),64)
            else:
                put(n+'_mv',rep(o['k']),64);put(n+'_mi',rep(o['k']),64)
                if n=='sel':put('sel',rep(o['k']),64)
        elif k=='kv_gather':
            read('sel',f"compressed.L{o['src']}");put(f"selected.L{o['src']}",rep(o['elems'],range(64)));missing=['selected_packed288B_row_route','paired_row_generation','QDQ4_decode_to_RF']
        elif k=='expert_fetch':
            read('route_ids');missing=['routed_expert_descriptor_to_bulk_copy','weight_resident_base_provider'];contract='selected experts sorted by ID; w1,w3,w2 immutable accepted descriptors'
        elif fn=='hc_mixes':
            read('h');a=o['which'];put(a+'_pre',rep(4));put(a+'_post',rep(4));put(a+'_comb',rep(16));put(a+'_res',rep(20480))
            missing=['HC_matrix_coefficients','ordered_chunk8_tree','EXP_poly_INT_compare','division','Sinkhorn20_loop'];contract='HC norm/chunk8; Sinkhorn20 ordered iterations; pre/post/comb separately rounded'
        elif fn=='hc_pre_norm':
            read('h','pre' if o['which']=='attn' else 'attn_pre');put('x',rep(5120));put(o['which']+'_x',rep(5120))
            missing=['ordered_seq4_BF16','ordered_chunk8_tree','division','INT_bit_seed','norm_gamma_provider']
        elif fn=='q_norm_kv_row':
            read('qa','kvraw',f"window.L{o['layer']}");put('qr',rep(1280));put('win_new',rep(512));put(f"window.L{o['layer']}",rep(128*512))
            missing=['norm_gamma_provider','ordered_chunk8_tree','INT_bit_seed','RoPE_table','QDQ8_encode_decode','selected_owner_write_visible']
        elif fn=='q_rope':
            read('q');put('q_own',rep(512,rs));missing=['RoPE_table','sign_bit_XOR','global_slice_lane_route']
        elif fn=='compressor':
            read('cmp',f"compressed.L{o['layer']}",f"index_keys.L{o['layer']}");put('new_ik',rep(128,rs));put('new_ckv',rep(512,rs));put(f"compressed.L{o['layer']}",[v*512 for v in owned(o['group']+1)],32,{'append_global_group':o['group']});put(f"index_keys.L{o['layer']}",[v*128 for v in owned(o['group']+1)],32,{'append_global_group':o['group']});missing=['persistent_open_group_owner','ordered_pool_and_norm','index_WK_matrix','RoPE_table','QDQ4_paired_append_visible']
        elif fn=='index_q':
            read('iq','iwr');put('iqf',rep(32*128));put('iw',rep(32));missing=['RoPE_table','QDQ4_quantizer','weight_scale_provider']
        elif fn=='index_scores':
            read('iqf','iw',f"index_keys.L{o['src']}");put('is_i',owned(o['n']),64);put('is_v',owned(o['n']),64)
            missing=['packed68B_row_provider','integer_dot_single_round','mixed_lane_transpose','BF16_round_pack','ordered_head32_chunk8_tree']
            contract='4 block32 dots single-round; padded seq8 combine; BF16; max+0; weight multiply/BF16; head32 chunk8/tree/BF16'
        elif fn=='cand_local':
            read('is_i','is_v');counts=[min(cfg['candidate_topk_blocks'],ceil(v,8)) for v in owned(o['n'])]
            put('cand_v',counts,64);put('cand_i',counts,64);put('cand_blocks',[ceil(v,8) for v in owned(o['n'])],64)
            missing=['owned_block_max','ordered_topk','pin_newest_block']
        elif fn=='cand_apply':
            read('cand_mv','cand_mi','cand_blocks');put('candidate_keep',b.byid[b.current['cand_blocks']]['elements_per_rank'],1);missing=['candidate_global_ID_lookup']
        elif fn=='cand_mask':
            read('is_i','is_v','candidate_keep');put('is_v',owned(o['n']),64);missing=['candidate_global_ID_lookup','select_negative_infinity']
        elif fn=='topk_local':
            read('is_i','is_v');put('sel_i',[min(o['k'],v) for v in b.byid[b.current['is_i']]['elements_per_rank']],64);put('sel_v',[min(o['k'],v) for v in b.byid[b.current['is_i']]['elements_per_rank']],64);missing=['ordered_topk','compare_global_ID_tie']
        elif fn=='attend':
            read('q_own',f"window.L{o['layer']}")
            if o['yarn']:read(f"selected.L{max(src for src in cfg['kv_source_layers'] if src<=o['layer'])}")
            put('o',[512 if r<64 else 0 for r in range(96)],32,[[r*512,(r+1)*512] if r<64 else [0,0] for r in range(96)]);put('o_own',rep(512,rs))
            missing=['QK_PV_ordered_chunk8_tree','EXP_poly_INT_compare','unrounded_denominator','sink_constant_provider','division','RoPE_table']
            contract='QK chunk8; max+EXP; BF16 PV input; unrounded denominator+sink; DIV/BF16; inverse RoPE'
        elif fn=='hc_post':
            a=o['which'];read('y' if a=='attn' else 'yf',a+'_res',a+'_post',a+'_comb');put('h',rep(20480))
            if a=='ffn':read('ffn_pre');put('pre',rep(4))
            missing=['ordered_seq4_BF16','cross_lane_coefficients']
        elif fn=='router_act':
            read('gsc');put('gsc',part(384),32,[[384*r//96,384*(r+1)//96] for r in range(96)]);missing=['softplus_EXP_DIV','IEEE_sqrt_RNE']
        elif fn=='route':
            read('gsc');put('router',rep(384));put('route_ids',rep(6),64);put('route_w',rep(6));missing=['bias_provider','router_top6_connect','ordered_seq6_den','division']
        elif fn=='swiglu':
            e=o['slot'];read(f'e{e}.g',f'e{e}.u')
            if e<6:read('route_w')
            # Partial write to persistent ea: old slices remain explicit dependencies.
            if 'ea' in b.current:read('ea')
            put('ea',rep(7*2304),32,{'slot':e,'full_extent':7*2304,'rank_local_slice':[[e*2304+2304*r//96,e*2304+2304*(r+1)//96] for r in range(96)]})
            missing=['EXP_poly_INT_compare','division','clamp_compare','BF16_round_pack','partial_buffer_merge']
        elif fn=='moe_sum':
            read(*[f'e{e}.d' for e in range(7)]);put('yf',part(5120),32,[[5120*r//96,5120*(r+1)//96] for r in range(96)])
            missing=['ordered_seq7_from_positive_zero','BF16_round_pack'];contract='7 expert sums in ascending ID/slot order from+0; BF16 once'
        elif fn=='final_norm':
            read('h','pre');put('x',rep(5120));missing=['ordered_seq4_BF16','ordered_chunk8_tree','division','INT_bit_seed','gamma_provider']
        elif fn=='argmax_local':
            read('logits');put('argmax_v',rep(1));put('argmax_i',rep(1),64);missing=['compare_global_ID_tie']
        elif fn=='engram_fetch':
            put('eg_rows',rep(8*3*256),32,{'full_extent':8*3*256,'dynamic_owner':'token_history_hash%96','owned_count_bound':8*3*256});missing=['token_history_hash_MOD96','Engram_E4M3_ue8_provider','Engram_deployment_shape']
        elif fn=='engram_mix':
            read('h','eg_kv');put('h',rep(20480));put('engram_h',rep(20480));missing=['Engram_weight_product','ordered_chunk8_tree','INT_bit_seed','IEEE_sqrt_RNE','EXP_poly_INT_compare','division','BF16_round_pack']
        else:raise ValueError('unhandled source opcode '+fn)
        b.op(fn,reads,w,pc,{'path':'tools/w19_hbm_tp96_isa.py','op':o},rs,missing,contract)
        pc+=1
    return b,g


def allocate(b):
    # A conservative serial macro policy: all participants' operands local to SM0.
    # RF slots persist to macro consumer retirement. Spill addresses are a distinct
    # proposed logical arena, never substituted for an actual resident HBM base.
    for v in b.values:v['retire_pc']=max(v['consumers'],default=v['birth_pc'])
    peaks=[]
    for rank in range(b.ranks):
        live={};spill_live={};spill_peak=rf_peak=0;rf=['KERNEL_WORKSPACE']*32+[None]*480
        events=sorted(b.values,key=lambda v:(v['birth_pc'],v['id']))
        for v in events:
            pc=v['birth_pc']
            for old in list(live):
                if b.byid[old]['retire_pc']<pc:
                    for slot in live.pop(old):rf[slot]=None
            for old in list(spill_live):
                if b.byid[old]['retire_pc']<pc:spill_live.pop(old)
            n=v['elements_per_rank'][rank];bits=v['bits_per_element']
            if not n:continue
            if v['name'].startswith(('window.','compressed.','index_keys.','selected.')):
                v['homes'].append({'rank':rank,'class':'persistent_or_selected_provider','bytes':ceil(n*bits,8),'resident_base':None,'required_endpoint':'versioned_persistent_or_selected_provider'});continue
            if not bits:
                v['homes'].append({'rank':rank,'SM':0,'class':'opaque_publication_identity','address':None,'bytes':None});continue
            size=ceil(n*bits,8);vectors=ceil(size,512);free=[i for i,x in enumerate(rf) if x is None]
            if vectors<=len(free):
                slots=free[:vectors];live[v['id']]=slots
                for slot in slots:rf[slot]=v['id']
                home={'rank':rank,'SM':0,'class':'RF','vector_slots':slots,'bytes':size,'bank_map':'4pages x16banks x256bits; page=slot>>7,row=slot&127','native_width_bits':4096}
            else:
                off=0
                for lo,hi in sorted(spill_live.values()):
                    if off+align(size)<=lo:break
                    off=max(off,hi)
                spill_live[v['id']]=(off,off+align(size));spill_peak=max(spill_peak,off+align(size))
                home={'rank':rank,'SM':0,'class':'spill_arena','byte_offset':off,'bytes':size,'resident_base':None,
                      'required_endpoint':'RF_spill_refill_with_versioned_owner'}
            v['homes'].append(home);rf_peak=max(rf_peak,sum(x is not None for x in rf))
        peaks.append({'rank':rank,'SM':0,'peak_RF_vectors':rf_peak,'peak_spill_arena_bytes':spill_peak,
          'shared_reserved_bytes':8192,'shared_staging_required_not_implemented':True})
    return peaks


def native(b):
    for o in b.operations:
        attrs=o['source'].get('attributes',{});dsop=o['source'].get('op',{})
        if o['opcode']=='MATRIX' or dsop.get('kind')=='mv':
            out=b.byid[o['writes'][0]];k=dsop.get('k');rows=dsop.get('n')
            if b.target=='Qwen':
                key=attrs['weight'];shape=out['elements_per_rank'];k=o['external_bindings']['immutable_weight_descriptor']['K']
                rows=max(shape)
            nc=16 if b.target=='Qwen' else 8
            o['matrix_port_lowering']={'module':'ot_gpu_sm_q' if b.target=='Qwen' else 'ot_gpu_sm_v','NC':nc,'rank_output_elements':out['elements_per_rank'],
              'whole_K':k,'global_rows':rows,'SM_assignment':'REQUIRES_COMPOSED_NATIVE_COLUMN_ROW_MAP',
              'xstore_broadcast_bytes_per_SM_full_K_bf16_path':k*2*nc,'xstore_accept_beat_bytes':256,
              'weight_response_bits':1024 if b.target=='Qwen' else 1088,'native_request_tag_bits':10,
              'capture_reserve_bytes_max':GEOMETRY['matrix_capture_bytes'][b.target],'actual_descriptor_c_g_base_lines':None,
              'round_order':o['golden_contract'],'duration_cycles':None}
            o['missing_native_endpoints']+=['full_shape_native_column_row_descriptor_map']
        if o['opcode'] not in ('RESIDUAL','SCALAR_MUL','ROW_SCALE'):continue
        if o['opcode']=='RESIDUAL':
            out=b.byid[o['writes'][0]];count=ceil(max(out['elements_per_rank']),128)
            o['native_lowering']={'endpoint':'ot_gpu_full_sm_service','ENABLE_required':1,'simd_mul':False,
              'vector_iterations_max_per_rank':count,'arity':2,'events_per_vector':[
              'simd_valid&&simd_ready','RF_READ_accept','held_RF_response_consume','OPERATE_FADD_LAT7',
              'RF_WRITE_both_copies','mirrored_ACK_consume','held_SIMD_done_consume'],
              'prior_unqualified_FSM_only_estimate_cycles':14,'measured_H1_alias_accept_cadence_cycles':19,'candidate_native_transaction_budget_cycles':19,'H1_calibration_scope':'DS same RF/SIMD sources; alias driver at10ns; Qwen shared endpoint transfer candidate only','clock_domain_candidate':'serial_0p9GHz',
              'candidate_measured_driver_transaction_budget':19*count,'RF_read_bits':count*8192,'RF_write_bits':count*4096,
              'rank_geometry_broadcasts':False,'qualified_cycles':None,'wire_ports':['simd_a[8:0]','simd_b[8:0]','simd_dst[8:0]'],
              'tail_zero_padding_provider_required':any(n%128 for n in out['elements_per_rank'])}
            o['missing_native_endpoints']+=['RF_tail_padding_and_compiler_dispatch']
        else:
            o['native_lowering']={'endpoint':'ot_gpu_full_sm_service','simd_mul':True,
               'vector_iterations_max_per_rank':ceil(max(b.byid[o['writes'][0]]['elements_per_rank']),128),'candidate_measured_driver_transaction_budget':19*ceil(max(b.byid[o['writes'][0]]['elements_per_rank']),128),
               'scalar_or_scale_broadcast_endpoint_missing':True,'qualified_cycles':None}
        if any(h['class']!='RF' for vid in o['reads']+o['writes'] for h in b.byid[vid]['homes']):
            o['missing_native_endpoints']+=['RF_spill_refill_with_versioned_owner']


def verify(b):
    for v in b.values:
        if v['retire_pc']<max(v['consumers'],default=v['birth_pc']):raise ValueError('early retirement')
        if len({h['rank'] for h in v['homes']})!=len(v['homes']):raise ValueError('duplicate home')
    for o in b.operations:
        for i in o['reads']:
            if b.byid[i]['birth_pc']>=o['pc']:raise ValueError('stale/forward operand')
        if o['timeline']['duration_term']!=f"T_{b.target}_{o['pc']}":raise ValueError('missing duration')
    for rank in range(b.ranks):
        active={}
        for v in sorted(b.values,key=lambda v:(v['birth_pc'],v['id'])):
            active={i:h for i,h in active.items() if b.byid[i]['retire_pc']>=v['birth_pc']}
            home=next((h for h in v['homes'] if h['rank']==rank),None)
            if home and home['class']=='RF':
                if any(s<32 or s>=512 for s in home['vector_slots']):raise ValueError('RF range')
                used={s for h in active.values() if h['class']=='RF' for s in h['vector_slots']}
                if used.intersection(home['vector_slots']):raise ValueError('live RF alias')
            if home and home['class']=='spill_arena':
                lo,hi=home['byte_offset'],home['byte_offset']+align(home['bytes'])
                if any(lo<h['byte_offset']+align(h['bytes']) and h['byte_offset']<hi for h in active.values() if h['class']=='spill_arena'):raise ValueError('live spill alias')
            if home:active[v['id']]=home
    return True


def norm_kernel(n,target):
    # Explicit source chunk8 rounding nodes; groups execute as a finite loop.
    # Tree parents retain child identity, with power-of-two zero padding.
    body=[];last='@POSZERO'
    for j in range(8):
        prod=f'p{j}';acc=f'a{j}'
        body += [{'op':'FMUL','dst':prod,'src':[f'x[{j}]',f'x[{j}]']},
                 {'op':'FADD','dst':acc,'src':[last,prod]}]
        last=acc
    groups=ceil(n,8);leaves=1<<(groups-1).bit_length();tree=[]
    current=[f'chunk[{i}]' if i<groups else '@POSZERO' for i in range(leaves)]
    level=0
    while len(current)>1:
        parents=[]
        for i in range(0,len(current),2):
            dst=f'tree{level}_{i//2}';tree.append({'op':'FADD','dst':dst,'src':current[i:i+2]});parents.append(dst)
        current=parents;level+=1
    meanop='FMUL' if target=='Qwen' else 'DIV'
    tail=[{'op':meanop,'dst':'mean','src':[current[0],'@INV_N' if target=='Qwen' else '@N']},
          {'op':'FADD','dst':'variance','src':['mean','@EPS']},
          {'op':'SHR','dst':'shift','src':['variance','@U1']},
          {'op':'ISUB','dst':'y0','src':['@RSQRT_SEED','shift']},
          {'op':'FMUL','dst':'half','src':['variance','@HALF']}]
    for i in range(3):
        tail += [{'op':'FMUL','dst':f'yy{i}','src':[f'y{i}',f'y{i}']},
          {'op':'FMUL','dst':f'hyy{i}','src':['half',f'yy{i}']},
          {'op':'XOR','dst':f'neg{i}','src':[f'hyy{i}','@SIGN']},
          {'op':'FADD','dst':f'corr{i}','src':['@ONEHALF',f'neg{i}']},
          {'op':'FMUL','dst':f'y{i+1}','src':[f'y{i}',f'corr{i}']}]
    for i in body+tree+tail:
        i['endpoint']='ot_gpu_full_sm_service.ADD' if i['op']=='FADD' else 'ot_gpu_full_sm_service.MUL' if i['op']=='FMUL' else 'MISSING_'+i['op']
        i['duration']='H1_ALIAS_DRIVER_19_FUNCTIONAL_CYCLES' if i['op'] in ('FADD','FMUL') else 'UNBOUND_'+i['op']
    vector_groups=ceil(groups,128)
    native_calls=vector_groups*16+len(tree)+sum(i['op'] in ('FMUL','FADD') for i in tail)
    demand={'issue_policy':'serialize all vector batches and scalar tree nodes; no ideal overlap',
      'native_ADD_MUL_transactions':native_calls,'RF_read_bits_upper':native_calls*8192,'RF_write_bits_upper':native_calls*4096,
      'measured_H1_driver_candidate_cycles_for_native_transactions_only':19*native_calls,'hardware_product_clock_conversion_qualified':False,
      'missing_instruction_cycles':None,'tree_scratch_load_store_transactions':2*len(tree)+len(tree),
      'scratch_transpose_and_broadcast_cost':None,'not_full_kernel_latency':True}
    return {'native_port_demand':demand,'shape':n,'source':'tools/qwen_hbm_complete_executor.py:chunk8/rstd/rsqrt' if target=='Qwen' else 'tools/w19_gpu_norm_calendar.py:scalar_norm_program + golden chunk8',
       'ordered_chunk_loop':{'tripcount':groups,'element_stride':8,'body':body,'result':last,'tail_inactive_elements_are_not_added':True},
       'tree':tree,'tail':tail,'shared_partial_bytes':groups*4,'shared_tree_materialized_bytes':4*(groups+len(tree)),
       'workspace_RF_slots':[0,32],'workspace_shared_byte_range':[0,8192],
       'shared_word_locations':{'chunk[i]':'4*i','tree_node[j]':f'{4*groups}+4*j'},
       'scratch_word_extract_insert_endpoint':None,'128lane_chunk_gather_endpoint':None,
       'tree_route_bytes_per_edge':4,'tree_transport_endpoint':None,
       'workspace_versions':'all dst names immutable; chunk[i] identifies loop invocation',
       'duration_cycles':None,'instructions_execute_on_cpu_oracle':False}


def hc_kernel(kind):
    instructions=[]
    for j in range(4):instructions.append({'op':'FMUL','dst':f'p{j}','src':[f'coefficient[{j}]',f'residual[{j}][lane]']})
    last='p0'
    for j in range(1,4):
        dst=f's{j}';instructions.append({'op':'FADD','dst':dst,'src':[last,f'p{j}']});last=dst
    if kind=='POST':
        instructions += [{'op':'FMUL','dst':'yp','src':['post[k]','y[lane]']},
                         {'op':'FADD','dst':'out','src':['yp',last]}];last='out'
    instructions += [{'op':'SHR','dst':'hi','src':[last,'@U16']},
      {'op':'AND','dst':'lsb','src':['hi','@U1']},
      {'op':'IADD','dst':'bias','src':[last,'@U7FFF']},
      {'op':'IADD','dst':'rounded','src':['bias','lsb']},
      {'op':'AND','dst':'bf16','src':['rounded','@UFFFF0000']}]
    for i in instructions:i['endpoint']='ot_gpu_full_sm_service.'+('ADD' if i['op']=='FADD' else 'MUL') if i['op'] in ('FADD','FMUL') else 'MISSING_'+i['op']
    return {'source':'tools/w19_gpu_norm_calendar.py:vector_program',
      'native_port_demand':{'native_ADD_MUL_transactions':(9 if kind=='POST' else 7)*40*(4 if kind=='POST' else 1),'native_H1_functional_cycle_candidate':19*(9 if kind=='POST' else 7)*40*(4 if kind=='POST' else 1),'BF16_INT_coefficients_and_transport_cycles':None},'instructions':instructions,'lane_iterations':5120,'post_k_iterations':4 if kind=='POST' else 1,
      'ordered_seq4_starts_at_p0':True,'BF16_round_bits':'source F32 bits +0x7fff+lsb, then mask',
      'workspace_RF_slots':[0,32],'coefficient_broadcast_endpoint':None,'duration_cycles':None}


def compact(b):
    for v in b.values:
        groups={}
        for h in v['homes']:
            k=json.dumps({key:value for key,value in h.items() if key!='rank'},sort_keys=True)
            groups.setdefault(k,[]).append(h['rank'])
        homes=[]
        for k,ranks in groups.items():
            h=json.loads(k);ranges=[]
            for r in ranks:
                if ranges and ranges[-1][1]==r:ranges[-1][1]=r+1
                else:ranges.append([r,r+1])
            h['rank_ranges']=ranges;homes.append(h)
        v['homes']=homes

def verify_tree(kernel):
    n=kernel['shape'];groups=ceil(n,8);leaves=1<<(groups-1).bit_length()
    current=[f'chunk[{i}]' if i<groups else '@POSZERO' for i in range(leaves)]
    cursor=0;level=0
    while len(current)>1:
        parents=[]
        for i in range(0,len(current),2):
            node=kernel['tree'][cursor];cursor+=1
            if node['src']!=current[i:i+2] or node['op']!='FADD':raise ValueError('golden tree order')
            parents.append(node['dst'])
        current=parents;level+=1
    if cursor!=len(kernel['tree']):raise ValueError('extra reduction node')
    last='@POSZERO'
    for j in range(8):
        node=kernel['ordered_chunk_loop']['body'][2*j+1]
        if node['src']!=[last,f'p{j}']:raise ValueError('golden chunk order')
        last=f'a{j}'
    return True

def calibration():
    base=ROOT/'results/uarch/h3_versioned_lowering_20261002/evidence'
    trace=json.loads((base/'H1_DS_trace_verdict.json').read_text())
    parent=json.loads((base/'H1_DS_parent_trace.json').read_text())
    run=json.loads((base/'H1_DS_run_verdict.json').read_text())
    if trace!=parent or trace['verdict']!='PASS_DIRECTED_CONNECTED_TRACE_ONLY':raise ValueError('H1 trace receipt')
    if run['verdict']!='PASS_DIRECTED_NATIVE_DS_CONNECTED_ONLY':raise ValueError('H1 terminal')
    for path in ('rtl/gpu/ot_gpu_full_sm_service.sv','rtl/gpu/ot_gpu_rf_service.sv'):
        if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=run['source_sha256'][path]:raise ValueError('H1 endpoint source mismatch')
    log=(base/'H1_DS_actual_sim.log').read_text();series={}
    if hashlib.sha256(log.encode()).hexdigest()!=run['logs_sha256']['DS/actual_sim.log']:raise ValueError('H1 raw log hash')
    if hashlib.sha256((base/'H1_DS_trace_verdict.json').read_bytes()).hexdigest()!=run['trace_sha256']['DS/trace_verdict.json']:raise ValueError('H1 trace hash')
    for case in trace['cases']:
        c=case['case'];pattern=rf'SIMD_ALIAS_ACCEPT case={c} pass=(\d+) index=(\d+) a=(\d+) b=(\d+) dst=(\d+) cycle=(\d+)'
        events=[tuple(map(int,m.groups())) for m in re.finditer(pattern,log)]
        if len(events)!=case['dependent_alias_operations']:raise ValueError('H1 operation coverage')
        if any(e[1]!=e[2] or e[2]!=e[3] or e[3]!=e[4] for e in events):raise ValueError('H1 alias address')
        if any(y[-1]-x[-1]!=19 for x,y in zip(events,events[1:])):raise ValueError('H1 alias cadence')
        series[c]={'accepts':len(events),'all_successive_accept_deltas':19,
          'first_accept':events[0][-1],'last_accept':events[-1][-1],**case}
    if series[3]['RF_fence_to_next_issue_cycles']!=9775 or series[4]['RF_last_visible_to_next_issue_cycles']!=10019:raise ValueError('H1 dependent fence')
    return {'source_commit':run['source_commit'],'binary_sha256':run['binary_sha256'],
      'cases':series,'functional_bench_clock_ns':10,'SSFF':False,'full_token_credit':False,
      'alias_driver_cadence_cycles':19,'Qwen_same_module_transfer':'model candidate; Qwen native chain measurement not inferred',
      'source_edge_estimate14_preserved_unqualified':True,'do_not_add_fixture_full_chain_9775_to_already_charged_alias_transactions':True,
      'source_endpoint_hardware_clock_or_product_ns_credit':False,
      'evidence_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(base.glob('H1*'))}}


def build():
    targets={};measured=calibration()
    for b in (qwen()[0],ds()[0]):
        peaks=allocate(b);native(b);verify(b);compact(b)
        for o in b.operations:
            o['boundary_demand']={'RF_input_bytes_per_rank':[sum(ceil(b.byid[i]['elements_per_rank'][r]*b.byid[i]['bits_per_element'],8) for i in o['reads']) for r in range(b.ranks)],
               'RF_output_bytes_per_rank':[sum(ceil(b.byid[i]['elements_per_rank'][r]*b.byid[i]['bits_per_element'],8) for i in o['writes']) for r in range(b.ranks)],
               'gather_reduce_payload_bytes':o['source'].get('op',{}).get('bytes'),
               'actual_route_source_dest_ports_bound':False}
            if o['opcode'] in ('RSTD','HEAD_NORM','FINAL_NORM'):
                o['kernel_binding']='Qwen_NORM128' if o['opcode']=='HEAD_NORM' else 'Qwen_NORM4096'
            elif o['opcode'] in ('hc_pre_norm','final_norm'):
                o['kernel_binding']=['DeepSeek_HC_PRE','DeepSeek_NORM5120']
                o['native_lowering']={'mixed_native_ADD_MUL_sequence':'DeepSeek_HC_PRE','missing_BF16_INT_and_coefficient_paths':True,'qualified_cycles':None}
            elif o['opcode']=='hc_post':
                o['kernel_binding']='DeepSeek_HC_POST'
                o['native_lowering']={'mixed_native_ADD_MUL_sequence':'DeepSeek_HC_POST','missing_BF16_INT_and_coefficient_paths':True,'qualified_cycles':None}
        targets[b.target]={'operations':b.operations,'operands':b.values,'storage_demand':peaks,
         'missing_endpoints':dict(sorted(Counter(e for o in b.operations for e in set(o['missing_native_endpoints'])).items())),
         'token_schedule':{'policy':'serial macro retirement, no ideal overlap','duration_expression':'+'.join(o['timeline']['duration_term'] for o in b.operations),
          'cycle_value':None,'every_operation_has_duration_term':True,'native_segment_cycles_conditional_only':True,'all_cost_terms_are_native_transactions_or_named_unbound_services':True},
         'summary':{'complete_macro_graph_visited':True,'all_hidden_external_operand_layouts_bound':False,'all_macros_expanded_to_native_instructions':False,'operations':len(b.operations),'immutable_versions':len(b.values),
          'native_path_operations':sum(o['native_lowering'] is not None for o in b.operations),
          'all_operations_hardware_admitted':False}}
    return {'schema':'opentallas.H3.versioned-lowering.v1','base_commit':BASE,'geometry':GEOMETRY,
      'source_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in PINS},
      'targets':targets,'actual_endpoint_calibration':measured,'ordered_kernels':{**{f'{t}_NORM{n}':norm_kernel(n,t) for t,n in [('Qwen',128),('Qwen',4096),('DeepSeek',5120)]},'DeepSeek_HC_PRE':hc_kernel('PRE'),'DeepSeek_HC_POST':hc_kernel('POST')},'unified_model_join':{'tool':'tools/uarch_model.py','symbols':['hbm_gpu_design','gpu_payload_transport_model','HBM_W19','HBM_TMEM'],
       'RF_physical_bits_per_SM':512*4096*2,'RF_physical_bytes_total':{'Qwen_HBM':2*32*524288,'DeepSeek_HBM':96*32*524288},'shared_physical_bytes_total':{'Qwen_HBM':2*32*65536,'DeepSeek_HBM':96*32*65536},'shared_physical_bits_per_SM':65536*8,
       'replicas_per_target':{'Qwen_HBM':2*32,'DeepSeek_HBM':96*32},
       'streaming_GHz':1.2,'serial_GHz':0.9,'route_tracks_area_slot_and_unknown_service_terms':'Maxwell admission required'},
      'four_target_composition':{'Qwen_HBM':'this complete lowering IR','DeepSeek_HBM':'this complete lowering IR',
       'Qwen_ROM':'unchanged separate emitted field; no GPU allocator substitution','DeepSeek_ROM':'unchanged reticle field ownership priority'},
      'hardware_or_timing_credit':False,'RTL_generated_or_run':False}

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);ap.add_argument('--verify',action='store_true');args=ap.parse_args()
    result=build()
    if args.verify:
        import gzip
        archived=json.loads((args.out/'model.json').read_text())
        if json.loads(json.dumps({k:v for k,v in result.items() if k!='targets'}))!=archived:raise ValueError('model replay mismatch')
        for target,data in result['targets'].items():
            with gzip.open(args.out/(target+'.json.gz'),'rt') as f:old=json.load(f)
            if data!=old:raise ValueError('lowering replay mismatch '+target)
        print(json.dumps({'status':'PASS_EXACT_COMPILER_REPLAY','targets':['Qwen','DeepSeek'],'RTL_runs':0,'native_clock_credit':False}))
        raise SystemExit(0)
    args.out.mkdir(parents=True,exist_ok=False)
    for target,data in result.pop('targets').items():
        with (args.out/(target+'.json')).open('x') as f:json.dump(data,f,separators=(',',':'));f.write('\n')
    (args.out/'model.json').write_text(json.dumps(result,indent=2)+'\n')
