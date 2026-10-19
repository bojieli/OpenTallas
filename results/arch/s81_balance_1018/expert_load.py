#!/usr/bin/env python3
"""S81-BALANCE: routed-expert load balance from REAL DeepSeek-V4.1-Flash router captures (MTP-STATS source).
Needs torch and the capture /tmp/claude-review-20261003/mtp_q/router/router_full.pt (sha256 86a9d9dab...).
Writes inputs_expert_load_holdout.json beside this file (compute.py reads it). Grade: measured (routing) +
modelled (placement). Placement is fitted on 60 random traces and evaluated on the other 60 (holdout)."""
import os
HERE = os.path.dirname(os.path.abspath(__file__))
import torch, json, numpy as np
d=torch.load('/tmp/claude-review-20261003/mtp_q/router/router_full.pt',map_location='cpu',weights_only=False)
E=384
def cat(ts):
    return np.concatenate([t['router_idx'][:, t['L']:, :].numpy() for t in ts],axis=1)
rng=np.random.default_rng(20261018); perm=rng.permutation(len(d))
fit=cat([d[i] for i in perm[:60]]); ev=cat([d[i] for i in perm[60:]]); allR=cat(d)
def freqs(R): return np.stack([np.bincount(R[l].ravel(),minlength=E) for l in range(40)]).astype(float)
Ff, Fe = freqs(fit), freqs(ev)
def place(f,D,rep=0):
    per=E//D; order=np.argsort(-f); load=np.zeros(D); cnt=np.zeros(D,int); db=np.zeros(E,int)
    for e in order:
        c=[k for k in range(D) if cnt[k]<per] or list(range(D))
        k=min(c,key=lambda k:load[k]); db[e]=k; load[k]+=f[e]; cnt[k]+=1
    return db
res={}
for D in (2,3,4,8,10,12):
    cont=[];hold=[];inS=[]
    for l in range(40):
        dc=np.minimum(np.arange(E)//(E//D),D-1)
        db=place(Ff[l],D)
        lc=np.bincount(dc,weights=Fe[l],minlength=D); lh=np.bincount(db,weights=Fe[l],minlength=D)
        cont.append(lc.max()/lc.mean()); hold.append(lh.max()/lh.mean())
    res[D]=dict(contiguous_mean=round(float(np.mean(cont)),3), contiguous_worst_layer=round(float(np.max(cont)),3),
                balanced_holdout_mean=round(float(np.mean(hold)),3), balanced_holdout_worst_layer=round(float(np.max(hold)),3))
print(json.dumps(res,indent=1))
json.dump(dict(method='fit LPT equal-count placement on 60 random traces (seed 20261018), evaluate per-group load on the other 60; contiguous = experts 0..E/D-1 in group 0 etc.; load = routed-expert hits over all decode positions (multi-user steady state)',
               source='/tmp/claude-review-20261003/mtp_q/router/router_full.pt sha256 86a9d9dab... (MTP-STATS source; 120 agentic greedy traces, 9,455 decode positions, top-6 of 384, 40 layers)',
               by_groups=res),open(os.path.join(HERE,'inputs_expert_load_holdout.json'),'w'),indent=1)
