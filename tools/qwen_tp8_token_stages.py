#!/usr/bin/env python3
"""Pin the 38 accepted functional stages to the exact native TAG59 layout."""
import argparse,hashlib,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
plan=json.loads(a.plan.read_text())
if (plan['stage_count'],plan['layers'],plan['tp'],plan['groups'])!=(38,36,8,3072):raise ValueError('native source plan')
stages=[{'stage':0,'kind':'embedding','program':'embedding_program.hex','segments':[0]}]
stages += [{'stage':layer+1,'kind':'decoder','layer':layer,'program':'layer_candidate_program.hex',
            'segments':[0,1,2],'program_bases':[0,14,22]} for layer in range(36)]
stages += [{'stage':37,'kind':'head','programs':[f'head_program_rank{rank}.hex' for rank in range(8)],
            'segments':[0],'final_norm_in_same_program':True,'terminal_segment':0}]
report={'schema':'opentallas.qwen-tp8-token-stage-tag.v1','source_plan_sha256':hashlib.sha256(a.plan.read_bytes()).hexdigest(),
        'functional_profile_only':True,'tag_bits':59,'fields':{'epoch':[58,43],'stage':[42,37],'token':[36,19],'position':[18,6],'segment':[5,0]},
        'epoch_owner':'sole central accepted-HOST-token allocator; POR retained, one active transaction; same epoch all38stages/all8ranks',
        'wrap_policy':'FFFF lock until all actual drains plus actual link reset and retraining completion; warm_ready never clears epoch state',
        'stage_count':38,'stages':stages,
        'return_contract':'Full TAG59 on every peer/local collective and native result return; reject mismatches before counters or VM commits',
        'terminal':{'stage':37,'segment':0,'required':'matching TAG59 plus original generation2 and actual KV/VM/collective/HOST drains'}}
a.out.write_text(json.dumps(report,indent=2)+'\n')
print('PINNED38STAGES_TAG59')
