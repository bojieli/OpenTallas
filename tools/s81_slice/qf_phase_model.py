#!/usr/bin/env python3
"""PRIVATE exact actual-return interval audit and deterministic pre-tree phase model.
No producer stimulus, deadline, golden output, or original programme is modified.
"""
import argparse,collections,gzip,json,re
from pathlib import Path
import cap_model as c
p=argparse.ArgumentParser();p.add_argument('log');p.add_argument('out');a=p.parse_args()
o=Path(a.out);o.mkdir(parents=True,exist_ok=True)
arr=[];groups=collections.defaultdict(list);L=[{}for _ in range(8)];stim={}
for line in gzip.open(a.log,'rt'):
 m=re.match(r'CAP_ARR t=(\d+) lane=(\d+) word=([0-9a-f]+)',line)
 if not m:continue
 t,l,w=int(m[1]),int(m[2]),int(m[3],16);tag=(w>>3)&0xffffffff
 z=dict(t=t,lane=l,word=m[3],tag=tag,row=(tag>>13)&65535,pos=tag>>29,lo=(tag>>8)&31,k=(tag>>5)&7,n=tag&31)
 assert l<6 and t not in L[l] and z['n']==3
 L[l][t]=(tag,(w>>35)&0xffffffff,(w>>67)&1,[len(arr)])
 stim[t]=stim.get(t,0)|(w<<(70*l));arr.append(z);groups[(z['pos'],z['row'])].append(z)
# Actual pair segment observations are independent of CAP return observations.
leaf={};leaf_events=0
pv=re.compile(r'ACTUAL_PAIR_PV t=(\d+) id=(\S+) valid=([01]+) rows=([0-9a-f]+) vals=([0-9a-f]+) seg=([0-9a-f]+) nseg=([0-9a-f]+) err=([01]+) pos=([0-9a-f]+)')
for line in gzip.open(a.log,'rt'):
 m=pv.match(line)
 if not m:continue
 t,pair,valid,rows,vals,seg,nseg,err,pos=m.groups()
 valid=int(valid,2);rows=int(rows,16);vals=int(vals,16);seg=int(seg,16);nseg=int(nseg,16);err=int(err,2);pos=int(pos,16)
 for k in range(2):
  if not(valid>>k&1):continue
  key=((pos>>(3*k))&7,(rows>>(16*k))&65535,(seg>>(5*k))&31)
  assert key not in leaf and (nseg>>(5*k))&31==3 and not(err>>k&1)
  leaf[key]=(vals>>(32*k))&0xffffffff;leaf_events+=1
assert leaf_events==len(leaf)==1536
for z in arr:
 vals=[leaf[(z['pos'],z['row'],j)] for j in range(3)]
 golden,_=c.golden_node(vals,z['lo'],z['k'],3)
 assert golden==(int(z['word'],16)>>35)&0xffffffff,('producer_partial_gold',z)
coverage=0;hist=collections.Counter()
for key,rs in groups.items():
 counts=collections.Counter()
 for z in rs:
  # Only genuine leaves of the RTL's normalized/padding-promoted node belong to it.
  counts.update(j for j in range(z['n']) if z['lo']<=j<z['lo']+(1<<z['k']))
 assert set(counts)==set(range(3)) and all(n==1 for n in counts.values()),(key,rs,counts)
 coverage+=len(counts);hist[len(rs)]+=1
assert len(arr)==652 and len(groups)==512 and coverage==1536
cfg=[]
for e in range(15):
 cfg.append((1700+600*e,dict(rbase=(((e+1)%4)<<14)|0x1800,rcnt=828,np=0,fmt=1,obase=0,ops=0,rsplit=0,lo32=0,hi32=0)))
models={}
for name,ds in [('original_tree',[0]*8),('phase64',[64*l for l in range(8)])]:
 lanes=[{t+ds[l]:w for t,w in x.items()}for l,x in enumerate(L)]
 r=c.model(lanes,cfg);models[name]=r
 if name=='phase64':assert not r['faults'] and len(r['writes'])==512
# Independent golden tree composition of ACTUAL returned partial payloads.
# This checks the CAP arithmetic composition; upstream producer-vs-checkpoint numeric remains separate.
def compose(rs,lo=0,k=2):
 for z in rs:
  if z['lo']==lo and z['k']==k:return (int(z['word'],16)>>35)&0xffffffff
 if k==0:raise AssertionError((rs,lo,k))
 left=compose(rs,lo,k-1)
 if lo+(1<<(k-1))>=3:return left
 return c.fadd(left,compose(rs,lo+(1<<(k-1)),k-1))[0]
expected={key:c.golden_row([leaf[(key[0],key[1],j)] for j in range(3)])[0] for key in groups}
assert all(expected[key]==compose(rs) for key,rs in groups.items())
for wr in models['phase64']['writes']:
 assert wr[4]==expected[(wr[6],wr[5])]
T=11900
with (o/'stim.hex').open('w') as f:
 for t in range(T):f.write(f'{stim.get(t,0):0140x}\n')
with (o/'expected.txt').open('w') as f:
 for wr in models['phase64']['writes']:
  edge,leaf,port,addr,data,row,pos,*_=wr;e=(edge-1700)//600
  f.write(f'{e} {leaf} {port} {addr} {data:08x}\n')
with (o/'cfg.txt').open('w') as f:
 for t,cf in cfg:
  d=(cf['fmt']<<27)|(cf['rbase']<<29)|(cf['rcnt']<<45)
  f.write(f'{t} {d:040x}\n')
summary=dict(words=652,rows=512,genuine_leaves=1536,intervals_exactly_once=True,row_partial_count_hist=dict(hist),
 actual_six_lane_max_added_edges=320,delta_vs_ED23=297,period=600,
 phase64_writes=512,phase64_faults=models['phase64']['faults'],
 original_tree_fault_hist=dict(collections.Counter(x[0] for x in models['original_tree']['faults'])),
 cap_arithmetic_matches_independent_actual_partial_tree=True,producer_segment_events=leaf_events,all652_actual_partials_match_producer_segment_golden=True,all512_CW_reference_is_producer_segment_golden=True,upstream_checkpoint_numeric_PASS=None,
 prospective_cap_cfg='15 new real commands at modeled1700+600e; not installed original programme',
 actual_return_payload_scope=True,production_deadline_fit=None,VP_drain_PASS=None)
(o/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
(o/'models.json').write_text(json.dumps(models,indent=2)+'\n')
(o/'actual_intervals.json').write_text(json.dumps(arr,indent=2)+'\n')
print(json.dumps(summary))
