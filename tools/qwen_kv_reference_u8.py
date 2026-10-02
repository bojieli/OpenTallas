"""Prepared post-only U8 reference producer; no callbacks into native execution.

Caller must source-qualify checkpoint/captures and perform the strict terminal
boundary audit before using the result. This does not reconstruct old KV events.
"""
import hashlib
import json
from pathlib import Path
import struct


def produce(native, checkpoint, captures, output):
    import numpy as np
    import torch
    from qwen_hbm_complete_executor import CheckpointWeights
    from qwen_hbm_complete_reference import PostExecutionReference
    import qwen3_deployment_quality as G
    captures=Path(captures);output=Path(output);output.mkdir(exist_ok=False)
    weights=CheckpointWeights(native['source_program'],checkpoint,row_batch=128)
    reference=PostExecutionReference(native['source_program'],weights)
    c=native['source_program']['config'];hd=c['head_dim'];kv=c['num_key_value_heads']//2
    nh=c['num_attention_heads']//2;context=native['source_program']['context_capacity']
    cos,sin=G.rope_tables_g([0],hd,c['rope_theta'],'cpu');records=[];payload={}
    try:
        for layer in range(36):
            x=weights.embedding(9707).copy() if layer==0 else np.load(captures/f'L{layer-1}.X.npy',allow_pickle=False).copy()
            x=torch.from_numpy(x)[None,:];r=G.rstd_g(x,c['rms_norm_eps'])[:,None]
            for rank in range(2):
                qkv=G.mul(reference.scaled_matrix(f'L{layer}.qkv.d{rank}',x),r)
                _,k,v=qkv.split([nh*hd,kv*hd,kv*hd],-1)
                k=G.rmsnorm_g(k.reshape(kv,hd),torch.from_numpy(weights.constant(layer,'k').copy()),c['rms_norm_eps'])
                prepack={'K':G.rope_g(k,cos,sin),'V':v.reshape(kv,hd)}
                values={kind:G.to_fp8(value) for kind,value in prepack.items()}
                for kind,value in prepack.items():
                    np.save(output/f'L{layer}.rank{rank}.{kind}.prepack.npy',value.detach().numpy().astype(np.float32),allow_pickle=False)
                extents={e['name']:e for e in native['source_program']['memory_allocation'][rank]['extents']}
                key=(layer,rank,0);payload[key]={}
                for kind,value in values.items():
                    if not torch.isfinite(value).all():raise ValueError('reference nonfinite')
                    # Independent golden Torch codec; never native pack8.
                    codes=value.to(torch.float8_e4m3fn).view(torch.uint8).numpy().reshape(kv,hd)
                    base=extents[f'L{layer}.{kind}']['base']
                    for head in range(kv):
                        for dim in range(hd):
                            offset=(head*(context//16)*hd+dim)*16 if kind=='K' else head*context*hd+dim
                            payload[key][base+offset]=int(codes[head,dim])
                data=b''.join(struct.pack('<QB',a,code) for a,code in sorted(payload[key].items()))
                filename=f'L{layer}.rank{rank}.reference_U8.bin';(output/filename).write_bytes(data)
                records.append(dict(key=key,file=filename,sha256=hashlib.sha256(data).hexdigest(),records=len(payload[key])))
                print(json.dumps(dict(event='INDEPENDENT_POST_ONLY_U8_REFERENCE',layer=layer,rank=rank)),flush=True)
        (output/'reference_inventory.json').write_text(json.dumps(records,indent=2)+'\n')
        (output/'checkpoint_reader_provenance.json').write_text(json.dumps(weights.provenance(),indent=2)+'\n')
        return payload
    finally:
        weights.cache.clear()
        weights.constants.clear()
