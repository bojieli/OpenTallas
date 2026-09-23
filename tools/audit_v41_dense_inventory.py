#!/usr/bin/env python3
"""Read checkpoint headers only and reconcile non-routed inventory categories."""
import hashlib
import json
import struct
import sys
from collections import defaultdict
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from opentallas.profiling import _weight_role
SNAPSHOT = Path('/home/ubuntu/.cache/huggingface/hub/models--deepseek-ai--DeepSeek-V4.1-Flash/snapshots/dba1be0a40aa45a94ad051997016db3960a90277')


def category(name):
    if not name.startswith('layers.'):
        return 'head' if name.startswith('head.') else 'final_norm'
    if '.engram.' in name: return 'engram_projection_and_gate'
    if '.ffn.shared_experts.' in name: return 'shared_expert'
    if '.ffn.gate.' in name: return 'router'
    if '.attn.indexer.' in name: return 'attention_indexer'
    if '.attn.compressor.' in name: return 'attention_compressor'
    if '.attn.' in name: return 'attention_projection_and_norm'
    if '.hc_' in name: return 'hyperconnection'
    return 'layer_norm'


def main():
    index_path=SNAPSHOT/'model.safetensors.index.json'
    index=json.loads(index_path.read_text())
    groups=defaultdict(lambda: {'bytes':0,'scale_bytes':0,'tensors':0})
    rows=[]; hashes={}
    for shard in sorted(set(index['weight_map'].values())):
        with (SNAPSHOT/shard).open('rb') as f:
            length=struct.unpack('<Q',f.read(8))[0]
            raw=f.read(length)
        hashes[shard]=hashlib.sha256(raw).hexdigest()
        for name,t in json.loads(raw).items():
            if name=='__metadata__' or _weight_role('deepseek_v41',name)!='decode_dense': continue
            assert index['weight_map'][name]==shard
            size=t['data_offsets'][1]-t['data_offsets'][0]
            kind=category(name);g=groups[kind]
            g['bytes']+=size;g['tensors']+=1
            if name.endswith('.scale'): g['scale_bytes']+=size
            rows.append({'name':name,'shape':t['shape'],'dtype':t['dtype'],'bytes':size,'category':kind})
    total=sum(g['bytes'] for g in groups.values())
    model_path='configs/models/candidates/deepseek-v4.1-flash.json'
    model=json.loads((ROOT/model_path).read_text())
    assert total==model['dense_weight_bytes']
    for g in groups.values(): g['fraction_of_dense']=g['bytes']/total
    out={'schema':'opentallas.v41-dense-inventory.v1','status':'checkpoint_inventory_reconciled_not_complete_runtime_read_ledger',
         'total_bytes':total,'categories':dict(sorted(groups.items())),
         'text_no_image_mask_known_inactive_bias_bytes':sum(r['bytes'] for r in rows if r['name'].endswith('.ffn.gate.bias_vl')),
         'text_no_image_mask_inventory_minus_known_inactive_bias_bytes':total-sum(r['bytes'] for r in rows if r['name'].endswith('.ffn.gate.bias_vl')),
         'tensor_rows':sorted(rows,key=lambda r:r['name']),
         'header_sha256':hashes,'index_sha256':hashlib.sha256(index_path.read_bytes()).hexdigest(),
         'limits':['Classification reuses the existing profile role policy; matching totals does not independently prove every tensor is read every token.',
                   'No tensor payload was loaded and no workload executed. Conditional router biases and other inactive branches still need runtime-role refinement.',
                   'KV compressed-owner reuse does not remove the per-layer sliding-window wkv projection.',
                   'Cache rankings require operator placement and critical-path service, not only category bytes.'],
         'input_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in (model_path,'src/opentallas/profiling.py','tools/audit_v41_dense_inventory.py')}}
    (ROOT/'results/architecture/v41_dense_inventory.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps(out['categories'],indent=2))


if __name__=='__main__': main()
