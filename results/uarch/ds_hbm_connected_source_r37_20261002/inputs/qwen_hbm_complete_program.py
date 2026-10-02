#!/usr/bin/env python3
"""Executable Qwen3-8B GPU graph compiler; no RTL or performance qualification."""
import argparse,hashlib,json,math,re
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CONFIG=ROOT/'compiler/models/qwen3-8b/config.json'
LOCK=ROOT/'compiler/models/qwen3-8b/checkpoint_source.json'
OPCODES={
 'EMBED':'checkpoint INT8 row decode + BF16 row scale',
 'RSTD':'chunk8 sum-of-squares tree + three-step reciprocal-square-root',
 'MATRIX':'INT8 x BF16 sequential contiguous chunks + exact pairwise tree',
 'ROW_SCALE':'FP32 multiply by checkpoint BF16 row scale',
 'SCALAR_MUL':'separate FP32 multiply by produced norm scalar',
 'QKV_SPLIT':'addressed view of die-local Q/K/V; no arrival-order gather',
 'HEAD_NORM':'per-head chunk8 RMSNorm + checkpoint Q/K gamma',
 'ROPE':'checkpoint-angle table and rounded FP32 rotate/multiply/add',
 'KV_WRITE':'actual produced K/V encoded into persistent provider memory',
 'KV_FENCE':'matching provider commit publication; never write acceptance',
 'KV_READ':'published persistent K/V read, including previous tokens',
 'SCORES':'BF16 query x cache, golden interleaved head-dimension tree',
 'EXP_SUM':'max, contract exp, chunk8 denominator; unnormalized BF16 weights',
 'PV':'cache V x unnormalized probabilities, interleaved context tree',
 'NORMALIZE':'separate produced reciprocal denominator multiply',
 'ALL_REDUCE':'TP rank-order FP32 reduction then shared BF16 row scale',
 'RESIDUAL':'FP32 add to actually produced preceding residual',
 'SILU_GATE':'contract exp/reciprocal SiLU, rounded multiply by up',
 'FINAL_NORM':'chunk8 RMSNorm and final checkpoint gamma',
 'ARGMAX':'global row index; exact ties choose lowest vocabulary ID',
 'ARGMAX_REDUCE':'TP ordered winner selection with global IDs'}

def split_for(rows,k,groups=6144):
    tiles=(rows+127)//128;best=None;s=1
    while s<=groups:
        if k%s==0:
            cycles=math.ceil(tiles/(groups//s))*(k//s)*8
            if best is None or cycles<best[0]:best=(cycles,s)
        s*=2
    return best[1]

def allocation(config,tp=2,context=8192):
    """128B striped, disjoint full-capacity ranges. No checkpoint bytes emitted."""
    h=config['hidden_size'];ff=config['intermediate_size'];v=config['vocab_size']
    nh=config['num_attention_heads'];kv=config['num_key_value_heads'];hd=config['head_dim']
    layout=[]
    for die in range(tp):
        cursor=0;extents=[]
        def put(name,size,role):
            nonlocal cursor
            cursor=(cursor+127)//128*128
            extents.append(dict(name=name,base=cursor,bytes=size,role=role));cursor+=size
        put('embedding',v*h+2*v,'immutable_checkpoint_W8')
        for layer in range(config['num_hidden_layers']):
            for name,rows,k in [('qkv',(nh+2*kv)*hd//tp,h),('o',h,nh*hd//tp),('gu',2*ff//tp,h),('down',h,ff//tp)]:
                put(f'L{layer}.{name}.codes',rows*k,'immutable_checkpoint_W8')
                put(f'L{layer}.{name}.scales',rows*2,'immutable_checkpoint_BF16_scales')
            put(f'L{layer}.qk_norm',2*hd*2,'immutable_checkpoint_BF16_constants')
            # Shipped K token16-interleave and contiguous V row addressing.
            put(f'L{layer}.K',kv//tp*context*hd,'persistent_FP8_K')
            put(f'L{layer}.V',kv//tp*context*hd,'persistent_FP8_V')
        put('head.codes',v//tp*h,'immutable_checkpoint_W8')
        put('head.scales',v//tp*2,'immutable_checkpoint_BF16_scales')
        put('final_norm',h*2,'immutable_checkpoint_BF16_constants')
        # Full position table owned by memory/constant provider, not golden injection.
        put('rope_table',context*hd*4,'immutable_checkpoint_derived_FP32_table')
        put('activation_scratch',4*(h*8+2*ff//tp+nh//tp*context),'activation_spill')
        stack_bytes=((cursor+127)//128+3)//4*128
        layout.append(dict(die=die,extents=extents,allocated_bytes=cursor,
            stack_count=4,stack_capacity_bytes=20250000000,
            max_stack_allocated_bytes=stack_bytes,capacity_fit=stack_bytes<=20250000000,
            addressing='global128Bline stripe stack=line%4,stackline=line//4;sector32B,AW34',
            residence_qualified=False,physical_slot_fit=False))
    return layout

def compile_program(config=None,tp=2,context=8192,groups=6144):
    c=dict(json.loads(CONFIG.read_text()) if config is None else config)
    h,hd,nh,kv,ff,v=(c[k] for k in ['hidden_size','head_dim','num_attention_heads','num_key_value_heads','intermediate_size','vocab_size'])
    if tp!=2 or nh%tp or kv%tp or ff%tp or v%tp or nh%kv or context%16:raise ValueError('TP2/full-context shape contract')
    if nh*hd!=h:raise ValueError('Qwen head/hidden extent mismatch')
    ops=[];producer={};registers={'token':[],'position':[]};weights={}
    def emit(op,inputs,outputs,shape,**attrs):
        index=len(ops);deps=sorted({producer[x] for x in inputs if x in producer})
        if any(x not in registers for x in inputs):raise ValueError('undefined instruction input')
        for name,size in zip(outputs,shape):
            if name in registers:raise ValueError('SSA register overwritten')
            registers[name]=size;producer[name]=index
        ops.append(dict(id=index,opcode=op,inputs=inputs,outputs=outputs,dependencies=deps,attributes=attrs))
        return outputs
    def matrix(layer,name,die,x,rows,k):
        key=f'L{layer}.{name}.d{die}' if layer is not None else f'head.d{die}'
        desc=dict(key=key,layer=layer,name=name,die=die,rows=rows,K=k,split=split_for(rows,k,groups),
            SMs=32,row_tiles_256_per_SM=math.ceil(math.ceil(rows/32)/256),
            quantize='full checkpoint output row -> fold declared norm -> W8codes/BF16scale -> TP slice; never re-quantize input-column shard',
            checkpoint_sources=([f'model.layers.{layer}.self_attn.{n}_proj.weight' for n in 'qkv'] if name=='qkv' else
                [f'model.layers.{layer}.mlp.{n}_proj.weight' for n in ['gate','up']] if name=='gu' else
                [f'model.layers.{layer}.self_attn.o_proj.weight'] if name=='o' else
                [f'model.layers.{layer}.mlp.down_proj.weight'] if name=='down' else ['lm_head.weight']),
            folded_norm=(f'model.layers.{layer}.input_layernorm.weight' if name=='qkv' else f'model.layers.{layer}.post_attention_layernorm.weight' if name=='gu' else None))
        weights[key]=desc;raw=key+'.raw'
        emit('MATRIX',[x],[raw],[[rows]],weight=key)
        if name in ('o','down'):return raw
        scaled=key+'.scaled';emit('ROW_SCALE',[raw],[scaled],[[rows]],weight=key);return scaled
    x='X.embed';emit('EMBED',['token'],[x],[[h]],checkpoint='model.embed_tokens.weight')
    for l in range(c['num_hidden_layers']):
        prefix=f'L{l}';r=prefix+'.r_input';emit('RSTD',[x],[r],[[]],epsilon=c['rms_norm_eps'])
        oparts=[];guparts=[]
        for die in range(tp):
            d=f'{prefix}.d{die}';qkv=matrix(l,'qkv',die,x,(nh+2*kv)*hd//tp,h)
            normalized=d+'.qkv_post';emit('SCALAR_MUL',[qkv,r],[normalized],[[(nh+2*kv)*hd//tp]])
            q,k,val=(d+'.'+n for n in ['q','k','v'])
            emit('QKV_SPLIT',[normalized],[q,k,val],[[nh//tp,hd],[kv//tp,hd],[kv//tp,hd]])
            qn=d+'.qn';kn=d+'.kn'
            emit('HEAD_NORM',[q],[qn],[[nh//tp,hd]],layer=l,kind='q',epsilon=c['rms_norm_eps'])
            emit('HEAD_NORM',[k],[kn],[[kv//tp,hd]],layer=l,kind='k',epsilon=c['rms_norm_eps'])
            qr=d+'.qr';kr=d+'.kr'
            emit('ROPE',[qn,'position'],[qr],[[nh//tp,hd]],theta=c['rope_theta'])
            emit('ROPE',[kn,'position'],[kr],[[kv//tp,hd]],theta=c['rope_theta'])
            ticket=d+'.write_ticket';fence=d+'.kv_fence'
            emit('KV_WRITE',[kr,val,'position'],[ticket],[[]],layer=l,die=die,format='fp8')
            emit('KV_FENCE',[ticket],[fence],[[]],layer=l,die=die)
            kc=d+'.cacheK';vc=d+'.cacheV'
            emit('KV_READ',[fence,'position'],[kc,vc],[[kv//tp,'position+1',hd]]*2,layer=l,die=die)
            score=d+'.scores';sc=min(hd,1<<(groups.bit_length()-1))
            pv=1<<(max(1,groups//max(1,hd//16)).bit_length()-1)
            emit('SCORES',[qr,kc],[score],[[nh//tp,'position+1']],head_groups=nh//kv,split=sc)
            exp=d+'.exp';den=d+'.den';emit('EXP_SUM',[score],[exp,den],[[nh//tp,'position+1'],[nh//tp]])
            att=d+'.pv';emit('PV',[exp,vc],[att],[[nh//tp,hd]],head_groups=nh//kv,split=pv)
            norm=d+'.att';emit('NORMALIZE',[att,den],[norm],[[nh//tp*hd]])
            oparts.append(matrix(l,'o',die,norm,h,nh//tp*hd))
        o=prefix+'.o';emit('ALL_REDUCE',oparts,[o],[[h]],rank_order=[0,1],post_scale_weight=f'L{l}.o.d0')
        residual=prefix+'.residual';emit('RESIDUAL',[x,o],[residual],[[h]])
        r=prefix+'.r_post';emit('RSTD',[residual],[r],[[]],epsilon=c['rms_norm_eps'])
        for die in range(tp):
            d=f'{prefix}.d{die}';gu=matrix(l,'gu',die,residual,2*ff//tp,h)
            scaled=d+'.gu_post';emit('SCALAR_MUL',[gu,r],[scaled],[[2*ff//tp]])
            act=d+'.act';emit('SILU_GATE',[scaled],[act],[[ff//tp]])
            guparts.append(matrix(l,'down',die,act,h,ff//tp))
        down=prefix+'.down';emit('ALL_REDUCE',guparts,[down],[[h]],rank_order=[0,1],post_scale_weight=f'L{l}.down.d0')
        result=prefix+'.X';emit('RESIDUAL',[residual,down],[result],[[h]]);x=result
    norm='head.norm';emit('FINAL_NORM',[x],[norm],[[h]],epsilon=c['rms_norm_eps'],checkpoint='model.norm.weight')
    winners=[]
    for die in range(tp):
        logits=matrix(None,'head',die,norm,v//tp,h);winner=f'head.d{die}.winner'
        emit('ARGMAX',[logits],[winner],[[]],global_row_offset=die*(v//tp));winners.append(winner)
    emit('ARGMAX_REDUCE',winners,['next_token'],[[]],rank_order=[0,1])
    for op in ops:
        attrs=op['attributes'];match=re.search(r'\.d([01])(?:\.|$)',op['outputs'][0])
        die=weights[attrs['weight']]['die'] if 'weight' in attrs else attrs.get('die',int(match.group(1)) if match else None)
        op['participants']=[die] if die is not None else [0,1]
        op['reads']=list(op['inputs']);op['writes']=list(op['outputs'])
        op['event_ids']={name:f"op{op['id']}.{name}" for name in ['issue','memory_read','write_commit','landing_accept','opcode_finish','result_visible','consumer_done','credit_return']}
        op['provider_key']=f"qwen.{op['opcode'].lower()}"
        op['loop_count']={'matrix_rows':weights[attrs['weight']]['rows'],'K':weights[attrs['weight']]['K'],'golden_split':weights[attrs['weight']]['split']} if 'weight' in attrs else {'outputs':registers[op['outputs'][0]],'context_limit':context}
        op['cost_cycles']={'fast':None,'serial':None,'DRAM':None,'NoC':None,'CDC':None,'credit_fence':None}
        op['physical_ports']={'RF_reads_bits_per_SM_serial_cycle':8192,'RF_writes_bits_per_SM_serial_cycle':4096,'shared_bytes_per_SM_serial_cycle':128,'shared_bytes_per_SM_fast_cycle_equivalent':96,'port_qualification':False}
    last_use={}
    for op in ops:
        for name in op['inputs']:last_use[name]=op['id']
    lowering_instructions={
        'EMBED':['GLOBAL_ROW_READ_INT8','RF_INT8_TO_F32','MUL_F32_BF16_SCALE'],
        'RSTD':['RF_READ','MUL_F32_SQUARE','SEQ8_ADD_F32','SHFL_PAIRWISE_TREE_F32','MUL_F32_INV_N','ADD_F32_EPS','BIT_RSQRT_SEED','NEWTON3_MUL_ADD_F32'],
        'MATRIX':['COALESCED_GLOBAL_READ','BULK_COPY_REG_SHARED','BF16_ACTIVATION','MMA_EXACT_SEQUENTIAL_CHUNKS','PAIRWISE_CHUNK_TREE_F32','ADDRESSED_ROW_COMMIT'],
        'HEAD_NORM':['SEQ8_SQUARE_SUM','SHFL_PAIRWISE_TREE_F32','RSQRT_NEWTON3','MUL_F32_X_R','MUL_F32_GAMMA'],
        'ROPE':['CONST_TABLE_READ','NEG_SIGN_XOR','MUL_F32','ADD_F32'],
        'KV_WRITE':['FP8_RNE_SATURATE','ADDRESSED_SECTOR_STORE','RETAIN_WRITE_TAG'],
        'KV_FENCE':['WAIT_ACTUAL_WR_VISIBLE','MATCH_EPOCH_PRODUCER','PUBLISH_AFTER_REQUIRED_COMMITS'],
        'KV_READ':['ACQUIRE_PUBLISHED_READER','GLOBAL_KV_READ','FP8_TO_BF16','RETAIN_READER_UNTIL_CONSUMER_DONE'],
        'SCORES':['BF16_Q','MMA_INTERLEAVED_HEAD_DIM','PAIRWISE_F32_TREE','MUL_F32_INV_SQRT_HD'],
        'EXP_SUM':['SHFL_MAX','ADD_F32_NEG_MAX','EXP_POLY_F32','SEQ8_SUM','PAIRWISE_TREE_F32','BF16_UNNORMALIZED_WEIGHTS'],
        'PV':['MMA_INTERLEAVED_CONTEXT','PAIRWISE_TREE_F32'],
        'NORMALIZE':['RECIP_NEWTON3','MUL_F32_ATTN'],
        'ALL_REDUCE':['FINITE_TP_SEND','RANK_ORDER_ADD_F32','WAIT_COLLECTIVE','MUL_F32_SHARED_ROW_SCALE'],
        'SILU_GATE':['NEG_SIGN_XOR','EXP_POLY_F32','ADD_F32_ONE','RECIP_NEWTON3','MUL_F32_GATE','MUL_F32_UP'],
        'FINAL_NORM':['SEQ8_SUM_SQUARE','PAIRWISE_TREE_F32','RSQRT_NEWTON3','MUL_F32_X_R','MUL_F32_GAMMA'],
        'ARGMAX':['ROW_TILE_SCAN','FCMP_STABLE_LOWEST_GLOBAL_ID','RETAIN_WINNER'],
        'ARGMAX_REDUCE':['FINITE_TP_WINNER_GATHER','FCMP_LOWEST_GLOBAL_ID'],
        'RESIDUAL':['RF_READ_2','ADD_F32'], 'SCALAR_MUL':['RF_READ_SCALAR_VECTOR','MUL_F32'],
        'ROW_SCALE':['BF16_SCALE_READ','MUL_F32'], 'QKV_SPLIT':['ADDRESSED_VECTOR_VIEW']}
    for op in ops:op['GPU_instructions']=lowering_instructions[op['opcode']]
    return dict(schema='opentallas.qwen-hbm-complete-program.v1',config=c,TP=tp,context_capacity=context,
        input_registers=['token','position'],result_register='next_token',instructions=ops,register_shapes=registers,
        weight_descriptors=weights,memory_allocation=allocation(c,tp,context),register_last_use=last_use,
        source_reuse={'shipped_program':'tools/hdc_qwen_fullshape_program_w12.py','weight_recipe':'tools/hdc_qwen_int8_image_w12.py','checkpoint_lock_revision':json.loads(LOCK.read_text())['revision'],'allocation_scope':'HBM128B striped companion extents reuse shipped tensor/TP dimensions and Ktoken16/Vcontiguous layouts; numerical capacity only, actual residence/provider not qualified'},
        contract='Existing shipped folded-W8 TP2 arithmetic; norms/postscales remain separately rounded; no new fusion/reordering',
        software_executable=True,actual_RTL_executed=False,full_token_RTL=False,
        modeled_token_cycles=None,headline_rate=None,engine_RTL_build_ready=False,physical_build_ready=False)

def coverage(program):
    counts=Counter(o['opcode'] for o in program['instructions']);entries={}
    for opcode,count in sorted(counts.items()):
        is_matrix=opcode in ('MATRIX','SCORES','PV')
        memory=opcode in ('EMBED','KV_WRITE','KV_FENCE','KV_READ')
        collective=opcode in ('ALL_REDUCE','ARGMAX_REDUCE')
        entries[opcode]=dict(instances=count,semantic_lowering=OPCODES[opcode],
            organization='Tensor-Core-style ordinaryGPU matrix' if is_matrix else 'finite GPU memory/fence provider' if memory else 'TP collective provider' if collective else 'ordinary GPU SIMT/RF/shared instructions',
            issue_ports='32SM/die,128matrixlanes/SM; circulatingIL8' if is_matrix else 'SIMT128lanes/SM,RF2R1W,shared32banks1R1W',
            resource_cycles={'matrix_issue':None,'SIMT_issue':None,'RF':None,'shared':None,'DRAM':None,'NoC':None,'CDC':None,'credits_fences':None},
            functional_provider='qwen_hbm_complete_executor.SoftwareGPUProvider',RTL_provider=None,
            software_is_DUT=False,complete_timing_admission=False)
    return dict(schema='opentallas.qwen-complete-lowering-coverage.v1',layers=program['config']['num_hidden_layers'],
        instruction_count=len(program['instructions']),matrix_descriptors=len(program['weight_descriptors']),opcodes=entries,
        all_semantics_lowered=set(counts)<=set(OPCODES),unknown_costs_fail_closed=True,
        full_shape_software_execution_qualified=False,actual_fulltoken_RTL=False,token_cycles=None,token_rate=None)
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);program=compile_program()
    for name,x in [('program.json',program),('lowering_coverage.json',coverage(program))]:
        with (a.out/name).open('x') as f:json.dump(x,f,indent=2);f.write('\n')
    print(json.dumps(dict(instructions=len(program['instructions']),layers=36,matrix_descriptors=len(program['weight_descriptors']),unknown_timing=True)))
