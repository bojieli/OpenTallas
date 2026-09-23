#!/usr/bin/env python3
"""Static eight-group attention projection placement and format sensitivity."""
import hashlib
import json
import math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SNAPSHOT=Path('/home/ubuntu/.cache/huggingface/hub/models--deepseek-ai--DeepSeek-V4.1-Flash/snapshots/dba1be0a40aa45a94ad051997016db3960a90277')


def partition(hidden=5120, heads=64, head_dim=512, groups=8, qrank=1280, orank=1024):
    if heads % groups: raise ValueError('Whole attention heads must fit groups')
    head_width=heads*head_dim//groups
    return {'groups':groups,'heads_per_group':heads//groups,
            'q_b_weights_per_group':head_width*qrank,
            'o_a_weights_per_group':orank*head_width,
            'o_b_weights_per_group':hidden*orank,
            'qrank_bf16_multicast_bytes':qrank*2,
            'o_rank_bf16_allgather_source_bytes':groups*orank*2,
            'o_b_fp32_partials_to_central_merge_bytes':groups*hidden*4,
            'o_b_central_merge_fp32_adds':(groups-1)*hidden}


def main():
    names=['compiler/models/deepseek-v4.1-flash/inference_config.json',
           'results/architecture/v41_dense_inventory.json',
           'configs/models/candidates/deepseek-v4.1-flash.json',
           'tools/audit_v41_attention_placement.py']
    cfg,inv,m=[json.loads((ROOT/n).read_text()) for n in names[:3]]
    # Official config is checked rather than silently imposing eight groups.
    assert cfg['n_heads']==64 and cfg['dim']==5120 and cfg['o_lora_rank']==1024
    rows=[r for r in inv['tensor_rows'] if '.attn.wo_a.' in r['name']]
    packed=sum(r['bytes'] for r in rows)
    values=sum(math.prod(r['shape']) for r in rows if r['name'].endswith('.weight'))
    bf16=values*2
    p=partition(cfg['dim'],cfg['n_heads'],cfg['head_dim'],cfg['o_groups'],cfg['q_lora_rank'],cfg['o_lora_rank'])
    out={'schema':'opentallas.v41-attention-placement.v1',
         'status':'placement_candidate_and_deployment_format_sensitivity_not_accepted_schedule',
         'partition':p,
         'o_a_storage':{'checkpoint_packed_bytes_all_layers':packed,
                        'vendor_bf16_materialized_bytes_all_layers':bf16,
                        'extra_bytes_if_materialized':bf16-packed,
                        'profile_active_weight_bytes':m['dense_weight_bytes']+m['routed_weight_bytes']*m['experts_per_token']//m['num_experts'],
                        'active_weight_bytes_with_only_o_a_materialized':m['dense_weight_bytes']+m['routed_weight_bytes']*m['experts_per_token']//m['num_experts']+bf16-packed},
         'central_o_b_merge_40_layers':{
             'ingress_bytes':cfg['n_layers']*p['o_b_fp32_partials_to_central_merge_bytes'],
             'sensitivity':[{'delivered_ingress_GB_s':bw,'fixed_one_way_us':lat,
                             'ingress_only_us':cfg['n_layers']*(lat+p['o_b_fp32_partials_to_central_merge_bytes']/(bw*1000))}
                            for bw in (100,400,900) for lat in (.1,.5,1)]},
         'limits':['Eight-group ownership is logical; groups may share a chip or span chips. No die count is selected.',
                   'q_a, local-window KV, sparse attention, normalization, scaling, query multicast and output publication are not priced by the o_b merge sensitivity.',
                   'o_b K-sharding creates partial sums. Vendor uses FP32 distributed reduction, but exact partial arithmetic and merge order still require a numerical contract.',
                   'o_a packed storage with on-read reconstruction may preserve vendor BF16 operands; applying FP8 GEMM instead is a separate arithmetic change.',
                   'Only o_a materialization changes in the format sensitivity; it is not the complete vendor GPU deployment, whose expert recast may also change bytes.',
                   'Central merge traffic includes all eight logical group contributions; local co-location may reduce external bytes. No in-network aggregation credit.',
                   'Allgather payload is unique source data, not total delivered or hop bytes. It trades communication association and dense weight layout against ordered K execution.'],
         'vendor_source_sha256':{n:hashlib.sha256((SNAPSHOT/n).read_bytes()).hexdigest() for n in ('inference/model.py','inference/convert.py')},
         'input_sha256':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in names}}
    (ROOT/'results/architecture/v41_attention_placement.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps(out,indent=2))


if __name__=='__main__':main()
