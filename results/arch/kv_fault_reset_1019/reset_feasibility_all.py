"""Necessary reset reach/depth bounds only; never a placement or reset-clear admission."""
import json, hashlib, re, math
from pathlib import Path
from collections import defaultdict, Counter
p=Path('/srv/opentallas-scratch/claude/codex-kv-output-contract-1019/gen4/reset_loads_all_branches.json')
d=json.loads(p.read_text()); nodes={}; groups=defaultdict(list)
def ck(s): return re.sub(r'\[0\]$','',s or '')
for n in d['existing_reset_nodes']:
    rid=n['root_id']; k=(rid,tuple(n['output_bit']))
    v=dict(root_id=rid,output_bit=n['output_bit'],xy=n['output_pin_xy'],clock=ck(n.get('clock')),depth=n['depth_from_root'],instance=n['instance'])
    if k in nodes: assert nodes[k]==v, (k,nodes[k],v)
    nodes[k]=v
for n in nodes.values():groups[(n['root_id'],n['clock'])].append(n)
rows=[]
# 43.2um is a deliberately permissive upper bound on a 12.96-square station's internal pin displacement.
# If even this generous geometric bound fails, no same-depth route can exist with these existing seeds.
for l in d['loads']:
    D=l['required_target_depth']; t=l['native_pin_xy']; opts=[]
    for n in groups[(l['root_details']['id'],ck(l['clock']))]:
        m=D-n['depth']
        if m<0:continue
        dist=sum(abs(a-b) for a,b in zip(t,n['xy']))
        budget=405*(m+1)+43.2*m
        if dist<=budget+1e-6:opts.append((m,dist,n))
    best=min(opts,key=lambda x:(x[0],x[1])) if opts else None
    rows.append(dict(instance=l['instance'],root=l['root_details']['id'],clock=ck(l['clock']),target_depth=D,status='NECESSARY_BOUND_ONLY' if best else 'NO_SEED_IN_COMPLETE_PROVIDED_RESET_TREE',minimum_new_stages_lower_bound=best[0] if best else None,seed=best[2] if best else None,target_xy=t))
out=dict(schema='codex.kv_reset_geometric_necessary.v1',qualified_release=False,source_manifest_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),source_manifest=str(p),load_count=len(rows),existing_seed_nodes=len(nodes),hop_bound_um=405,per_added_station_pin_displacement_upper_bound_um=43.2,status_counts=dict(Counter(r['status'] for r in rows)),minimum_stage_histogram=dict(Counter(str(r['minimum_new_stages_lower_bound']) for r in rows)),limitations=['Seed inventory covers all existing descendants exported for relevant reset roots; no new root/clock crossing or release-calendar change considered.','No obstacle routing/placement, fanout, clock phase, reset assertion/release or source-clear propagation proof; passing this necessary geometric bound is not admission.','Added cells must bind actual native closed reset/clock views; no old load or release changed.'],loads=rows)
q=Path('/srv/opentallas-scratch/claude/qwen-kvsys/codex-canonical-landlag/reset_feasibility_all_branches.json');q.write_text(json.dumps(out,indent=1)+'\n');print(json.dumps({k:v for k,v in out.items() if k!='loads'}))
