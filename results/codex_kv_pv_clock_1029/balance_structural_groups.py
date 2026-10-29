#!/usr/bin/env python3
"""Exact-count geometric assignment preserving complete short pipeline families."""
import json,re,sys,collections,copy
from pathlib import Path
import numpy as np
from scipy.optimize import milp,Bounds,LinearConstraint
from scipy.sparse import lil_matrix
from group_pipeline_sinks import norm,family

def group(s):
 t=norm(s);a=t.split('$')[0];side=t[:4]
 m=re.match(r'u_s([01])\.u_slice\.old\[\d+\]\[(\d+)\]',a)
 if m:return side+'.old_bit'+m[2]
 m=re.match(r'u_s[01](?:\.u_slice\.tree_sum|\.ts)\[(\d+)\]',a)
 if m:return side+'.output_pair'+m[1]
 # These complete families are direct shift/control pipelines: never split.
 if re.search(r'\.(fc|tc|wp|cp|lastp|fp|commit_c)(?:\[|$)',a):return side+'.control_pipelines'
 # Command/replica bits drive controls together; preserve them as one family.
 if re.search(r'\.(c_r|cx_r)(?:\[|$)',a):return side+'.command'
 return a

def main(v):
 root=Path(__file__).parent;d=json.load(open(root/f'pv_tree_lane_atomic_{v}.json'))
 leaves=[l for l in d['core_tree']['leaves']if l.get('cts_open')];nodes={n['name']:n for n in d['core_tree']['nodes']};roots=[l['node']for l in leaves]
 base=json.load(open(root/'input'/f'base_{v}.json'));target={l['node']:len(l['sinks'])for l in base['core_tree']['leaves']if l.get('cts_open')}
 own={s:l['node']for l in leaves for s in l['sinks']};fixed={s:n for s,n in own.items()if family(s)}
 groups=collections.defaultdict(list)
 for s in own:
  if s not in fixed:groups[group(s)].append(s)
 pos={}
 for line in (root/'input'/f'geom_{v}.tsv').read_text().splitlines():
  a=line.split('\t')
  if a[0]=='C'and len(a)>=9:pos[norm(a[8])]=((float(a[4])+float(a[6]))/2,(float(a[5])+float(a[7]))/2)
 keys=sorted(groups);N=len(keys);A=lil_matrix((N+4,N*4));cost=[];upper=[]
 for i,k in enumerate(keys):
  for j,n in enumerate(roots):
   ds=[abs(pos[norm(s).rsplit('/',1)[0]][0]-nodes[n]['xy_um'][0])+abs(pos[norm(s).rsplit('/',1)[0]][1]-nodes[n]['xy_um'][1])for s in groups[k]]
   cost.append(sum(ds)+1e-6*j);upper.append(1 if max(ds)<=405 else 0)
   A[i,4*i+j]=1;A[N+j,4*i+j]=len(groups[k])
 fixedcount=collections.Counter(fixed.values());b=np.array([1]*N+[target[n]-fixedcount[n]for n in roots])
 res=milp(np.array(cost),integrality=np.ones(N*4),bounds=Bounds(np.zeros(N*4),np.array(upper)),constraints=LinearConstraint(A.tocsc(),b,b),options={'time_limit':45,'mip_rel_gap':.001})
 assert res.x is not None,res.message
 after=dict(fixed);gd=[]
 for i,k in enumerate(keys):
  j=int(np.argmax(res.x[4*i:4*i+4]));assert res.x[4*i+j]>.999
  n=roots[j];after.update({s:n for s in groups[k]});gd.append(dict(group=k,size=len(groups[k]),root=n))
 counts=collections.Counter(after.values());assert all(counts[n]==target[n]for n in roots)
 for l in leaves:l['sinks']=[s for s,n in after.items()if n==l['node']];l['domain_sinks']=len(l['sinks'])
 ds=[abs(pos[norm(s).rsplit('/',1)[0]][0]-nodes[n]['xy_um'][0])+abs(pos[norm(s).rsplit('/',1)[0]][1]-nodes[n]['xy_um'][1])for s,n in after.items()]
 d['core_tree']['equal_load']=True
 d['plan']+=' | exact original leaf counts via spatial assignment of complete old-bit chains, tree_sum/ts pairs and control families'
 report=dict(view=v,counts=dict(counts),FP_family_count=32,nonFP_group_count=N,solver=res.message,max_stub_L1_um=max(ds),over405=sum(x>405 for x in ds),groups=gd,changed_sinks=[dict(sink=s,old=own[s],new=n)for s,n in after.items()if n!=own[s]],scope='geometric exact-count structural grouping; no electrical/clock latency tuning')
 (root/f'pv_tree_structural_balanced_{v}.json').write_text(json.dumps(d,indent=1)+'\n');(root/f'balanced_{v}.json').write_text(json.dumps(report,indent=1)+'\n');print(v,{k:report[k]for k in report if k not in ['groups','changed_sinks']})
if __name__=='__main__':main(sys.argv[1])
