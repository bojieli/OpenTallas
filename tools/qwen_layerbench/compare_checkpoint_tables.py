#!/usr/bin/env python3
"""Fresh full-checkpoint comparison of the prepared36-layer table manifest.

Runs on the fleet. Checkpoint copying may still be in progress: completed
shards are consumed in layer order, with explicit progress; no time limit.
Final PASS additionally requires all locked checkpoint file hashes.
"""
import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1<<20),b''):h.update(block)
    return h.hexdigest()


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for name in ('snapshot','gold-root','lowering-root','manifest','out'):
        ap.add_argument('--'+name,type=Path,required=True)
    a=ap.parse_args()
    lock_path=a.gold_root/'compiler/models/qwen3-8b/checkpoint_source.json'
    lock=json.loads(lock_path.read_text())
    expected={e['path']:e for e in lock['expected_files']}
    if a.snapshot.name!=lock['revision']:raise ValueError('checkpoint revision differs from lock')
    def wait_file(name):
        path=a.snapshot/name;last_report=0
        while not path.is_file() or path.stat().st_size!=expected[name]['size_bytes']:
            if time.monotonic()-last_report>60:
                print('WAITING_FOR_CHECKPOINT_COPY',name,flush=True);last_report=time.monotonic()
            time.sleep(5)
        return path
    for name in ('config.json','model.safetensors.index.json'):
        if sha(wait_file(name))!=expected[name]['sha256']:raise ValueError('checkpoint metadata hash: '+name)
    config=json.loads((a.snapshot/'config.json').read_text())
    if config['num_hidden_layers']!=36:raise ValueError('checkpoint is not36-layer release')
    index=json.loads((a.snapshot/'model.safetensors.index.json').read_text())['weight_map']
    manifest=json.loads(a.manifest.read_text())
    if manifest['source']['checkpoint_sha256']!=sha(lock_path):raise ValueError('manifest checkpoint lock differs')
    sys.path.insert(0,str(a.lowering_root/'tools/qwen_layerbench'))
    sys.path.insert(0,str(a.gold_root/'tools'))
    import torch
    from safetensors import safe_open
    import hdc_qwen_int8_image_w12 as Q
    import hdc_qwen_layer0_rom_w12 as R
    import dv_lower as D
    import dv_lower_mat as M
    import dv_lower_vec as V
    torch.set_num_threads(8)
    own=D.ownership();cr=V.crom_map(own)
    result=dict(schema='opentallas.qwen.all36-checkpoint-table-compare.v1',
        verdict='IN_PROGRESS',checkpoint_revision=lock['revision'],checkpoint_lock_sha256=sha(lock_path),
        torch_version=torch.__version__,
        manifest_sha256=sha(a.manifest),layers=[],checkpoint_hashes={},
        source_sha256={str(Path(m.__file__).name):sha(Path(m.__file__)) for m in (Q,R,D,M,V)})
    names=('self_attn.q_proj.weight','self_attn.k_proj.weight','self_attn.v_proj.weight',
        'self_attn.o_proj.weight','mlp.gate_proj.weight','mlp.up_proj.weight','mlp.down_proj.weight',
        'input_layernorm.weight','post_attention_layernorm.weight','self_attn.q_norm.weight','self_attn.k_norm.weight')
    def tensor(key):
        with safe_open(str(a.snapshot/index[key]),framework='pt',device='cpu') as sf:
            return sf.get_tensor(key).float().numpy()
    for n in range(36):
        shards=sorted({index[f'model.layers.{n}.'+suffix] for suffix in names})
        for name in shards:wait_file(name)
        source=Q.layer_tp2_matrices(a.snapshot,n,0)
        matrices=R.joined_matrices(source)
        f32=lambda x:(np.asarray(x,dtype=np.uint32)<<16).view(np.float32)
        scales=dict(qkv=f32(matrices['qkv'][1]),gu=f32(matrices['gu'][1]),
                    o=np.ones(4096,dtype=np.float32),down=np.ones(4096,dtype=np.float32))
        b=M.btab_stream(M.btab_layout(own),scales)
        c=V.crom_table(own,cr,dict(ps1=f32(matrices['o'][1]),ps2=f32(matrices['down'][1]),
            q_norm=tensor(f'model.layers.{n}.self_attn.q_norm.weight'),
            k_norm=tensor(f'model.layers.{n}.self_attn.k_norm.weight')))
        stage=next(s for s in manifest['stages'] if s['stage']==n+1)
        for sl in stage['slices']:
            s=sl['slice']
            got_b=[dict(addr=addr,payload_hex=f'{pay:0256x}') for addr,pay in b[s]]
            got_c=[dict(addr=addr,payload_hex=f'{pay:0256x}') for dst,addr,pay in c if dst in (s,15)]
            if got_b!=sl['btab'] or got_c!=sl['crom']:
                result['verdict']='FAIL';result['failure']=dict(layer=n,slice=s,btab_equal=got_b==sl['btab'],crom_equal=got_c==sl['crom'])
                a.out.write_text(json.dumps(result,indent=2)+'\n')
                raise ValueError('fresh checkpoint table mismatch '+str(result['failure']))
        result['layers'].append(dict(layer=n,slices=12,checkpoint_shards=shards,verdict='PASS'))
        a.out.write_text(json.dumps(result,indent=2)+'\n')
        print('CHECKPOINT_STATIC_TABLE_LAYER_PASS',n,flush=True)
        del source,matrices
    for name,e in expected.items():
        if name.endswith('.safetensors') or name in ('config.json','model.safetensors.index.json'):
            digest=sha(wait_file(name));result['checkpoint_hashes'][name]=digest
            if digest!=e['sha256']:raise ValueError('checkpoint content hash mismatch '+name)
    result['verdict']='PASS'
    a.out.write_text(json.dumps(result,indent=2)+'\n')
    print('ALL36_FRESH_CHECKPOINT_TABLE_PASS',flush=True)


if __name__=='__main__':main()
