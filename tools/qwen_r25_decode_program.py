#!/usr/bin/env python3
"""TP4 r25 pre-norm graph, actual c12 words, and fail-closed host lowering.

SU words use the existing vec campaign ABI, not a production dispatcher ISA.
Missing production kernel bindings prevent link(); no invented entry PCs.
"""
import argparse, hashlib, importlib, json, math, sys
from pathlib import Path
H, FF, V, L, TP, CTX = 4096, 12288, 151936, 36, 4, 8192
VM_WORDS=1<<18
RESIDUAL, NEXT, GAIN = 229376,233472,237568


def service_address(global_byte):
    """Explicit global stripe -> real mapper37 tuple; never narrow to Waddr24."""
    if type(global_byte)!=int or global_byte<0:raise ValueError('byte address')
    line,offset=divmod(global_byte,128)
    stack=line%4;local=(line//4)*128+offset
    if local>=1<<35:raise ValueError('stack-local mapper extent')
    sector=local>>5
    pc=((sector>>2)^(sector>>7)^(sector>>12))&31
    return dict(byte_address37=(stack<<35)|local,stack=stack,local_byte=local,
                sector30=sector,canonical_pc=pc,byte_in_sector=local&31,
                native_weight24_translation=None)


def kv_sweep_address(row0,position,sector_in_row):
    """Proposed KVS32 transpose; row0 allocation must be bound by service owner."""
    if not 0<=row0<1<<15 or not 0<=position<8192 or not 0<=sector_in_row<4:raise ValueError('KV extent')
    s=position*4+sector_in_row;p=s%32;j=s//32
    return dict(pc=p,j=j,bank=(((j>>7)&7)<<2)|(j&3),row=row0+(j>>10),col=(j>>2)&31,
                row0_allocated=False)


def load_su(tools):
    sys.path.insert(0,str(Path(tools).resolve()))
    programs=importlib.import_module('qwen_r25_su_programs')
    rope=importlib.import_module('qwen_r25_su_stage')
    return programs,rope,programs.C,programs.I


def su_programs(tools):
    S,R,C,I=load_su(tools)
    def op(**fields):
        f=C.op_defaults();f.update(fields);C.encode(f);return f
    norm=S.norm_program(1,H,x=RESIDUAL,gain=GAIN,scalar=16384,y=0)
    norm.append(op(nout=1,nin=H,abase=0,asi=1,rnd=1,dst=I.DST_VM,obase=0,osi=1))
    qk=S.norm_program(8,128,x=0,gain=8192,scalar=12288,y=16384)
    qk+=S.norm_program(2,128,x=1024,gain=8320,scalar=12296,y=17408)
    # Actual rotate-half words, relocated to consume normalized Q/K.
    rope=[]
    for f in R.program():
        f=dict(f);f['abase']+=16384;f['cbase']+=16384;f['obase']-=8192;rope.append(f)
    silu=S.swiglu_program()
    silu.append(op(nout=1,nin=3072,abase=8192,asi=1,rnd=1,dst=I.DST_VM,obase=8192,osi=1))
    scale=[op(nout=1,nin=1536,abase=0,asi=1,bbase=8192,bsi=1,m1=I.M1_AB,dst=I.DST_VM,obase=0,osi=1)]
    residual=[op(nout=1,nin=H,abase=RESIDUAL,asi=1,cbase=NEXT,csi=1,ad=I.AD_C,dst=I.DST_VM,obase=RESIDUAL,osi=1)]
    stages=dict(round_q=[op(nout=1,nin=1024,abase=0,asi=1,rnd=1,dst=I.DST_VM,obase=0,osi=1)],prenorm=norm,qknorm=qk,rope=rope,softmax=S.softmax_program(),swiglu=silu,row_scale_qkv=scale,residual=residual)
    paths=[Path(S.__file__),Path(R.__file__),Path(C.__file__),Path(I.__file__)]
    return dict(abi='vec_campaign_PFIELDS',word_bits=C.PW,production_dispatcher=False,
        programs={name:dict(fields=ops,words_hex=[format(C.encode(f),'x') for f in ops]) for name,ops in stages.items()},
        source_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})


def matrix(rows,k):
    # Front C ABI: 8 interleaved beats per group, NC8 independent columns.
    return dict(op_fmt=3,ENABLE_INT8=1,op_c=8,op_g=math.ceil(k/512),op_gs=1,
        active_columns=1,physical_columns=8,K=k,output_rows=rows,
        SMs=[dict(sm=s,row_begin=rows*s//32,row_end=rows*(s+1)//32,
                  op_rows=rows*(s+1)//32-rows*s//32) for s in range(32)],
        line_payload_bytes=136,weight_code_bytes=128,line_stride_bytes=160,
        payload_rule='two consecutive issue-order 64-code beats; eight zero sidecar bytes,24 transport padding bytes',
        operand_rule='k=(g*64+lane)*8+t; NC columns are independent activation vectors',
        image_qualified=False,producer_binding=None,op_xb_extent=math.ceil(k/512)*8)


def layout():
    cursor=0;extents=[]
    def put(name,size,role):
        nonlocal cursor
        cursor=(cursor+127)//128*128
        extents.append(dict(name=name,base=cursor,bytes=size,role=role));cursor+=size
    put('embedding.codes',V*H,'replicated immutable W8 codes')
    put('embedding.scales',V*2,'replicated BF16 row scales')
    for l in range(L):
        for name,r,k in [('qkv',1536,H),('o',H,1024),('gu',6144,H),('down',H,3072)]:
            put(f'L{l}.{name}.lines',r*(k//128)*160,'fmt3 transport160 candidate')
            put(f'L{l}.{name}.scales',r*2,'BF16 scales')
        put(f'L{l}.input_norm',H*2,'unfolded BF16 gain')
        put(f'L{l}.post_norm',H*2,'unfolded BF16 gain')
        put(f'L{l}.qk_norm',256*2,'Q/K BF16 gains')
        for kv in range(2):
            for plane in ('K','V'):put(f'L{l}.kv{kv}.{plane}',CTX*128,'persistent FP8 pos128 contiguous')
    put('head.lines',(V//TP)*(H//128)*160,'fmt3 transport160 candidate')
    put('head.scales',V//TP*2,'BF16 head scales')
    put('final_norm',H*2,'unfolded BF16 gain')
    put('rope.cos_signed_sin',CTX*256*4,'position-indexed FP32 constants')
    put('activation_spill',VM_WORDS*4,'VM backing if required')
    return dict(per_die=extents,replicated_embedding=True,die_count=4,allocated_bytes=cursor,
        stack_count=4,stack_capacity_bytes=20250000000,max_stack_allocated_bytes=math.ceil(cursor/512)*128,
        stripe='global128B line: stack=line%4,local=(line//4)*128+offset; real mapper37=(stack<<35)|local; sector30=local>>5; PC=s[6:2]^s[11:7]^s[16:12]',
        mapper_source_commit='4cc9fe7bc',native_weight24_translation=None,
        KV_successor=dict(kind=1,row0_allocated=False,slots_required=144,nsec_per_pc_per_head_plane=1024,pc_mask=4294967295,
            transpose='logical sector=pos*4+s; p=sector%32;j=sector//32; bank={j[9:7],j[1:0]};row=row0+(j>>10);col=j[6:2]',
            descriptor='chd[16:2]=row0,[28:17]=nsec,[60:29]=mask; K and V sweeps separate; 4096 nsec cannot fit12bits',
            physical_base_conversion=None,sustained90pct=False,downstream_credit_qualified=False,
            global_extents_scope='capacity/logical offsets only; native transpose and actual row0 allocation must replace direct global KV access'),
        service_binding_qualified=False,transport_efficiency=128/160)


def compile_program(su_tools, image_tools=None):
    su=su_programs(su_tools);batches=[];nextid=0
    image_shapes=None;image_pin=None
    if image_tools is not None:
        sys.path.insert(0,str(Path(image_tools).resolve()))
        image=importlib.import_module('qwen_r25_int8_image');image_shapes=image.qwen_tp4_shapes()
        image_pin=hashlib.sha256(Path(image.__file__).read_bytes()).hexdigest()
    def batch(name,spec):
        nonlocal nextid
        ops=[]
        for kernel,unit,reads,writes,params in spec:
            if unit=='SM' and image_shapes is not None:
                names={'qkv':['q','k','v'],'gu':['gate','up']}.get(kernel,[kernel])
                params['image_manifest_geometry']={n:image_shapes[n] for n in names}
            row=dict(id=nextid,kernel=kernel,unit=unit,reads=reads,writes=writes,
                dependency=(None if nextid==0 else nextid-1),parameters=params,
                production_entry=None,stage_words=su['programs'].get(kernel))
            ops.append(row);nextid+=1
        batches.append(dict(name=name,operations=ops,command_words_needed=len(ops)+1))
    batch('embedding', [('embedding','HBM_SU',['host.token'],['vm.residual'],dict(row_stride=H,scale_stride=2,token_bits=18))])
    for l in range(L):
        batch(f'L{l}',[
          ('prenorm','SU',['vm.residual',f'L{l}.input_norm'],['vm.norm'],dict(input_base=RESIDUAL,output_base=0)),
          ('qkv','SM',['vm.norm',f'L{l}.qkv.lines'],['vm.qkv_raw'],dict(components={n:matrix(r,H) for n,r in [('q',1024),('k',256),('v',256)]})),
          ('row_scale_qkv','SU',['vm.qkv_raw',f'L{l}.qkv.scales'],['vm.qkv','vm.v'],dict(views=dict(q=[0,1024],k=[1024,1280],v=[1280,1536]),scale_artifact='row_scales_bf16.bin; opaque released row bits')),
          ('qknorm','SU',['vm.qkv',f'L{l}.qk_norm'],['vm.qkn'],dict(q_heads=8,k_heads=2,dim=128)),
          ('rope','SU',['vm.qkn','host.position','rope.cos_signed_sin'],['vm.qr','vm.kr'],dict(theta=1e6,dim=128)),
          ('round_q','SU',['vm.qr'],['vm.qr_bf16'],dict(rounding='BF16 after RoPE; K/V use FP8 append')),
          ('kv_append','HBM',['vm.kr','vm.v','host.position'],[f'L{l}.write_ticket'],dict(writes_per_die=4,bytes_per_row=128)),
          ('kv_fence','HBM',[f'L{l}.write_ticket'],[f'L{l}.kv_visible'],dict(completion='actual posted-write visibility')),
          ('attention_qk','ATTN',['vm.qr_bf16',f'L{l}.kv_visible'],['vm.scores'],dict(q_heads=8,kv_heads=2,context=CTX,lanes_per_kv=4)),
          ('softmax','SU',['vm.scores'],['vm.bf16_exp','vm.denominator'],dict(exp_is_unnormalized=True)),
          ('attention_pv','ATTN',['vm.bf16_exp',f'L{l}.kv_visible'],['vm.pv'],dict(dim=128)),
          ('pv_normalize','SU',['vm.pv','vm.denominator'],['vm.attention'],{}),
          ('o','SM',['vm.attention',f'L{l}.o.lines'],['vm.o_partial'],matrix(H,1024)),
          ('all_reduce_o','TU',['vm.o_partial'],['vm.o_sum'],dict(ranks=[0,1,2,3],words=H)),
          ('row_scale_o','SU',['vm.o_sum',f'L{l}.o.scales'],['vm.next'],{}),
          ('residual','SU',['vm.residual','vm.next'],['vm.residual'],dict(residual_base=RESIDUAL,next_base=NEXT)),
          ('prenorm','SU',['vm.residual',f'L{l}.post_norm'],['vm.norm'],dict(input_base=RESIDUAL,output_base=0)),
          ('gu','SM',['vm.norm',f'L{l}.gu.lines'],['vm.gu_raw'],dict(components={n:matrix(3072,H) for n in ['gate','up']})),
          ('row_scale_gu','SU',['vm.gu_raw',f'L{l}.gu.scales'],['vm.gu'],dict(gate_base=0,up_base=4096,scale_artifact='row_scales_bf16.bin; opaque released row bits')),
          ('swiglu','SU',['vm.gu'],['vm.act'],dict(gate_base=0,up_base=4096,out_base=8192)),
          ('down','SM',['vm.act',f'L{l}.down.lines'],['vm.down_partial'],matrix(H,3072)),
          ('all_reduce_down','TU',['vm.down_partial'],['vm.down_sum'],dict(ranks=[0,1,2,3],words=H)),
          ('row_scale_down','SU',['vm.down_sum',f'L{l}.down.scales'],['vm.next'],{}),
          ('residual','SU',['vm.residual','vm.next'],['vm.residual'],dict(residual_base=RESIDUAL,next_base=NEXT))])
    batch('head',[
        ('prenorm','SU',['vm.residual','final_norm'],['vm.norm'],dict(input_base=RESIDUAL)),
        ('head','SM',['vm.norm','head.lines'],['vm.logit_raw'],matrix(V//TP,H)),
        ('head_scale','SU',['vm.logit_raw','head.scales'],['vm.logits'],{}),
        ('argmax_local','ARGMAX',['vm.logits'],['vm.local_winner'],dict(rows=V//TP,local_index_bits=17)),
        ('argmax_gather','TU',['vm.local_winner'],['vm.winners'],dict(ranks=[0,1,2,3])),
        ('argmax_merge','SU',['vm.winners'],['host.next_token'],dict(global_index_bits=18,ids='exact FP32 die_base + local_idx; lowest ID ties'))])
    missing=sorted({o['kernel'] for b in batches for o in b['operations'] if not o['stage_words']})
    return dict(schema='opentallas.qwen_r25_decode_program.v1',contract='r25_prenorm_full_w8',
        targets=dict(TP=4,layers=36,hidden=H,FFN=FF,vocab=V,context=CTX),batches=batches,
        fmt3_matrix_geometry=image_shapes,fmt3_source_sha256=image_pin,
        SU=su,HBM=layout(),VM=dict(words=VM_WORDS,units='FP32 word addresses',persistent_residual=[RESIDUAL,RESIDUAL+H],next=[NEXT,NEXT+H],norm_gain=[GAIN,GAIN+H],
            temporal_overlays='QKV/QK/RoPE precede attention; softmax uses words0..196623; residual/next/gain persist above229376; loader must transpose packed gate/up into bases0/4096'),
        missing_SU_or_service_programs=missing,missing_production_entries=sorted({o['kernel'] for b in batches for o in b['operations']}),
        full_decode_executable=False,full_token_RTL=False,physical_qualification=False,headline_rate=None,
        host_policy='38 host batches; load each only after all8 CP halves retire; actual kernel dispatch required; no synthetic result computation')


def link(program,bindings):
    """Resolve actual production dispatch entries; completeness precedes admission."""
    linked=[]
    for b in program['batches']:
        words=[]
        for o in b['operations']:
            k=o['kernel'];bind=bindings.get(k)
            if not bind:raise ValueError('missing actual production kernel binding: '+k)
            if bind.get('unit')!=o['unit'] or not bind.get('production_dispatch') or not bind.get('kernel_sha256'):
                raise ValueError('unqualified unit/dispatcher/source binding: '+k)
            pc=bind.get('entry_pc');mask=bind.get('sm_mask');imem=bind.get('imem_words',16384)
            if type(pc)!=int or type(imem)!=int or not 0<=pc<imem or type(mask)!=int or not 0<mask<1<<16:raise ValueError('invalid launch PC/mask')
            words.append((1<<60)|(mask<<44)|pc)
        words.append(2<<60)
        if len(words)>256:raise ValueError('command memory extent')
        linked.append(dict(name=b['name'],words=words,result=(b['name']=='head'),
                           descriptor_plan=b['operations'],requires_descriptor_installation=True))
    return linked


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--su-tools',required=True,type=Path);ap.add_argument('--image-tools',required=True,type=Path);ap.add_argument('--out',required=True,type=Path);ap.add_argument('--bindings',type=Path)
    a=ap.parse_args();p=compile_program(a.su_tools,a.image_tools)
    if a.bindings:p['linked_command_batches']=link(p,json.loads(a.bindings.read_text()))
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(p,indent=2)+'\n')
if __name__=='__main__':main()
