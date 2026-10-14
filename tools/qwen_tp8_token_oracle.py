#!/usr/bin/env python3
"""Faithful checkpoint-derived native cold-token reference; observer only."""
import argparse, gc, hashlib, json
from pathlib import Path
import numpy as np
import hdc_golden as G
from hdc_qwen_int8_image_w12 import shipped_vocab_rows
from qwen_tp8_native_layer_oracle import generate

def run(images,snapshot,out,layers,token):
    if not 1<=layers<=36:raise ValueError('layer count')
    out.mkdir(parents=True,exist_ok=False)
    report={'scope':'INDEPENDENT_EXPECTED_VALUES_ONLY_NOT_RTL_EXECUTION','token':token,'position':0,
            'context':1,'prior_cache':'empty: zero previous tokens; no synthetic previous K/V',
            'production_collective_order':'pair rankp+rank(p+4), then package0..3 left fold','layers':[]}
    previous=None;x=None
    for layer in range(layers):
        directory=out/f'layer{layer}'
        result=generate(images/f'layer{layer}',snapshot,directory,position=0,token=token,
                collective_profile='production_tp8_two_level',layer=layer,x_input=x,previous_vm=previous)
        if any((directory/f'die{rank}'/f'prior_{kind}_fp8.bin').stat().st_size for rank in range(8) for kind in ('K','V')):
            raise AssertionError('cold token must not have prior rows')
        report['layers'].append({'layer':layer,'oracle_sha256':hashlib.sha256((directory/'oracle.json').read_bytes()).hexdigest()})
        previous=directory;x=directory/'die0/X_final_fp32.hex'
        (out/'token_oracle_progress.json').write_text(json.dumps(report,indent=2)+'\n');gc.collect()
    if layers==36:
        # Head SU operations: recompute SSX, RX=rsqrt(SSX/H+eps), H=(X*RX)*norm.
        from safetensors import safe_open
        index=json.loads((snapshot/'model.safetensors.index.json').read_text())['weight_map']
        with safe_open(str(snapshot/index['model.norm.weight']),framework='pt',device='cpu') as sf:
            norm=sf.get_tensor('model.norm.weight').float().numpy()
        values=G.from_bits(np.array([int(w,16) for w in x.read_text().split()],dtype=np.uint32))
        ssx=G.lane_sum(G.mul(values,values))
        rx=G.rsqrt(G.add(G.mul(ssx,np.float32(1/4096)),np.float32(1e-6)))
        normalized=G.mul(G.mul(values,rx),norm)
        (out/'head_H_expected.hex').write_text(''.join(f'{int(v):08x}\n' for v in G.bits(normalized)))
        bests=[]
        for rank in range(8):
            logits=np.empty(18992,dtype=np.float32)
            for begin in range(0,18992,256):
                end=min(begin+256,18992)
                weights=shipped_vocab_rows(snapshot,'lm_head',start=begin,count=end-begin,die=rank)
                raw=G.matvec(weights['codes'].numpy().astype(np.float32),normalized,512)
                logits[begin:end]=G.mul(raw,weights['scales'].float().numpy().reshape(-1))
            if not np.isfinite(logits).all():raise ValueError('unsupported nonfinite head output')
            local=int(np.argmax(logits));global_index=rank*18992+local
            bests.append({'rank':rank,'local_index':local,'global_index':global_index,'value_bits':int(G.bits(logits[local]))})
            (out/f'head_rank{rank}_expected_logits.hex').write_text(''.join(f'{int(v):08x}\n' for v in G.bits(logits)))
            print('HEAD_REFERENCE',rank,global_index,flush=True)
        best=max(bests,key=lambda b:(float(G.from_bits(np.uint32(b['value_bits']))),-b['global_index']))
        report.update(head_rank_argmax=bests,next_token=best['global_index'],next_val_bits=best['value_bits'])
    report['complete_38_stage_reference']=layers==36
    (out/'token_oracle_progress.json').write_text(json.dumps(report,indent=2)+'\n')
    print('REFERENCE_COMPLETE',layers,flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--images',type=Path,required=True);p.add_argument('--snapshot',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);p.add_argument('--layers',type=int,default=36);p.add_argument('--token',type=int,default=0)
    a=p.parse_args();run(a.images,a.snapshot,a.out,a.layers,a.token)
