#!/usr/bin/env python3
"""Header-only census of every released SM matrix at actual TP96 compiler ownership.

No tensor payload, synthetic numerical model, or inference is evaluated. Physical
bytes include the immutable136-byte weight/scale records, all routed experts,
all40 backbone layers, three DSpark layers and the full language-model head.
"""
import hashlib,json,math
from pathlib import Path
import rtl_v41_fullshape_layer_campaign as LC
import w19_hbm_tp96_isa as W
from dsrom_checkpoint import Checkpoint
ROOT=Path(__file__).resolve().parents[1]

def run(out):
    ck=LC.Checkpoint();m,model_sha=LC.build_model(ck,engram=False)
    raw=Checkpoint();entries={};headers={};totals=[[0]*32 for _ in range(96)]
    def add(op,layer):
        if op['kind']!='mv':return
        w=op['w'];P=m.P(layer) if layer>=0 else ''
        if isinstance(w,tuple) and isinstance(w[0],int):
            slot,mat=w
            if slot<m.k_exp:
                key=P+'ffn.experts.*.'+mat+'.weight';copies=m.n_exp
                names=[P+f'ffn.experts.{e}.{mat}.weight' for e in range(copies)]
            else:key=P+f'ffn.shared_experts.{mat}.weight';copies=1;names=[key]
        elif isinstance(w,list):key='|'.join(w);copies=1;names=w
        else:key=w;copies=1;names=[w]
        # Runtime expert slots refer to the SAME stored expert table.
        identity=(layer,key,op['fn'])
        if identity in entries:return
        meta=[]
        for name in names:
            d=raw.descriptor(name)[2]
            headers[name]=d;meta.append(d)
            if d['dtype'] in ('F8_E4M3','I8'):
                scale_name=name[:-len('.weight')]+'.scale'
                scale=raw.descriptor(scale_name)[2];headers[scale_name]=scale
                columns=d['shape'][1]*(2 if d['dtype']=='I8' else 1)
                expected=[d['shape'][0] if d['dtype']=='I8' else math.ceil(d['shape'][0]/32),math.ceil(columns/32)]
                assert scale['dtype']=='F8_E8M0' and scale['shape']==expected,(scale_name,scale,expected)
        shape_rows=sum(x['shape'][0] for x in meta) if isinstance(w,list) else meta[0]['shape'][0]
        assert shape_rows==op['n'],(key,shape_rows,op['n'])
        if not isinstance(w,list):assert all(d['shape'][0]==op['n'] for d in meta),(key,'expert row mismatch')
        if op['fn']!='wo_a_part':
            for d in meta:
                width=d['shape'][1]*(2 if d['dtype']=='I8' else 1)
                assert width==op['k'],(key,width,op['k'])
        fmt=op['fmt'] if op['fn']=='linear_q' else 'bf16'
        rowbytes=8*math.ceil(op['k']/dict(bf16=512,fp8=1024,fp4=2048)[fmt])*136
        rankbytes=[];rankrows=[]
        for rank,(lo,hi) in enumerate(op['rows']):
            if op['out']=='logits':lo=rank*math.ceil(op['n']/96);hi=min(op['n'],lo+math.ceil(op['n']/96))
            count=max(0,hi-lo);rankrows.append([lo,hi]);rankbytes.append(count*rowbytes*copies)
            for sm in range(32):
                own=max(0,(count+31-sm)//32)
                totals[rank][sm]+=copies*128*math.ceil(own*rowbytes/128)
        entries[identity]=dict(layer=layer,key=key,format=fmt,experts=copies,source_tensors=names,
            source_rows=op['n'],source_k=op['k'],source_function=op['fn'],
            packed_bytes_per_row=rowbytes,rank_row_intervals=rankrows,rank_useful_bytes=rankbytes,
            row_to_sm='local output row ordinal modulo32; first13 L0wq_a rows match released SM00..12 distribution',
            physical_copy_or_descriptor_mapping_qualified=False)
    for layer in range(m.L):
        for op in W.Compiler(m,1048575,'oreduce').compile_layer(layer,True):add(op,layer)
    m.ratio=list(m.ratio_all);m.n_exp=m.dspark_n_exp;m.k_exp=m.dspark_k_exp
    for layer in range(m.L,m.L+m.n_mtp):
        for op in W.Compiler(m,1048575,'oreduce').compile_layer(layer,True):add(op,layer)
    for op in W.Compiler(m,1048575,'oreduce').compile_head():add(op,-1)
    # Additional literal SM producers in ds_native.Lower.compressor and MTP seed/Markov.
    for source in m.kv_src:
        add(dict(kind='mv',w=m.P(source)+'attn.indexer.wk.weight',fn='linear_bf16',fmt='bf16',
            n=128,k=512,rows=[[0,128] for _ in range(96)],out='KIN'),source)
    add(dict(kind='mv',w='mtp.0.main_proj.weight',fn='linear_q',fmt='fp8',n=m.dim,k=3*m.dim,
        rows=W.even(m.dim),out='y'),40)
    add(dict(kind='mv',w='mtp.2.markov_head.head.weight',fn='mv',fmt='bf16',n=129280,k=256,
        rows=W.even(129280),out='logits'),42)
    assert m.w.loaded_bytes==0 and raw.read_bytes==0
    result=dict(schema='opentallas.hbm.checkpoint-residency.v1',status='ACTUAL_HEADERS_AND_COMPILER_OWNERSHIP_CAPACITY_CENSUS',
        source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in ['tools/hbm_checkpoint_residency.py','tools/w19_hbm_tp96_isa.py','tools/hgi_sim/ds_native.py','tools/hgi_sim/ds_mtp_kernels.py','tools/rtl_v41_fullshape_layer_campaign.py','tools/hdc_golden_v41.py','tools/dsrom_checkpoint.py','compiler/models/deepseek-v4.1-flash/inference_config.json']},
        checkpoint_index_sha256=hashlib.sha256((raw.root/'model.safetensors.index.json').read_bytes()).hexdigest(),
        checkpoint_revision=raw.root.name,model_init_source_sha256=model_sha,checkpoint_tensor_header_count=len(headers),
        checkpoint_header_manifest_sha256=hashlib.sha256(json.dumps(headers,sort_keys=True).encode()).hexdigest(),
        checkpoint_payload_bytes_read=raw.read_bytes,numerical_weight_bytes_decoded=m.w.loaded_bytes,
        matrices=list(entries.values()),rank_sm_reserved_bytes=totals,
        rank_total_bytes=[sum(x) for x in totals],max_rank_bytes=max(map(sum,totals)),max_sm_bytes=max(map(max,totals)),
        existing_datawin_reservation_bytes_per_sm=254*131072,
        datawin_only_all_checkpoint_fits=all(v<=254*131072 for row in totals for v in row),
        required_additional_inventory=['HC and scalar/tables live in separately protected source-fixed regions',
            'actual source fixed CKV/IKS/MTP/DMA ranges and lifetime compatibility',
            'actual source-backed install descriptors/loader ACK/compiled native programmes',
            'physical pin/root/route/timing/performance qualification'])
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=1)+'\n');raw.close()
    print(json.dumps({k:result[k] for k in ('checkpoint_tensor_header_count','checkpoint_payload_bytes_read','max_rank_bytes','max_sm_bytes','datawin_only_all_checkpoint_fits')}))
    return result
if __name__=='__main__':run(ROOT/'results/arch/hbm_die_v15/checkpoint_residency/receipt.json')
