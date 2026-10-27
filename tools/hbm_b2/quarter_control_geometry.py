#!/usr/bin/env python3
"""Source-identity control/meta placement proposal for native static_h quarter.
No RTL/plan edits, no added storage/cycles; reset delivery remains separately owned.
"""
import argparse,json,math,collections
from pathlib import Path
import numpy as np
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
ap=argparse.ArgumentParser();ap.add_argument('--data',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
D=a.data;L=json.load(open(D/'c11_native/layout.json'));P=[{p['name']:p for p in json.load(open(D/f'pins_h{h}.json'))}for h in range(2)]
L['tails'][0]['origin_um'][1]=950.4;L['tails'][0]['orient']='MX';L['tails'][1]['origin_um'][1]=1209.6;L['tails'][1]['orient']='R0'
W,H=218.592,187.488;obs=L['cores']+L['tails']+L['srams']
def free(p):
 x,y=p
 return not any(z['origin_um'][0]-.27<x<z['origin_um'][0]+z['outline_um'][0]+.27 and z['origin_um'][1]-.27<y<z['origin_um'][1]+z['outline_um'][1]+.27 for z in obs)
def point(pin,e,c,k,h):
 p=P[h][pin];return (8.64+c*449.28+h*224.64+p['x'],8.64+e*1391.04+[0,267.84,483.84,751.68][k]+(H-p['y']if k%2 else p['y']))
def l1(x,y):return abs(x[0]-y[0])+abs(x[1]-y[1])
arcs=[];anchors={};bad=[]
def ff(name,p):
 p=list(p)
 if name in anchors and anchors[name]!=p:raise ValueError('conflicting physical identity '+name)
 anchors[name]=p;return name

def arc(src,dst,sp,dp,kind):
 d=l1(sp,dp);r=dict(source=src,target=dst,source_um=list(sp),target_um=list(dp),kind=kind,length_um=round(d,6));arcs.append(r)
 if d>405+1e-6:bad.append(r)
def regarc(src,dst,sp,dp,kind):ff(src,sp);ff(dst,dp);arc(src,dst,sp,dp,kind)
# Existing quarter scalar registers, separate from keybuf address FFs.
# Common point is a bank anchor; actual cells must be spread by joint packing.
for name in ['qv_r','bv_r','h_r']+[f'bi_r[{b}]'for b in range(8)]+[f'nk_r[{b}]'for b in range(12)]:ff(name,(230.256,1173.744))
for name in ['ke_r']+[f'kb_r[{b}]'for b in range(171)]+[f'rk_r[{b}]'for b in range(7)]+[f'fo_r[{b}]'for b in range(11)]:ff(name,(194.4,1160))
for line in range(4):
 for bit in range(11):ff(f'kl_r[{line*1099+bit}]',(194.4,[1006.64,1046.64,1306.64,1346.64][line]))
# Independent leaf control banks follow the exact same source f/g stage identities;
# data bits may remain in their source-aware key/query banks.
FQ=[[(230.256,772.5),(690,700),(1128.816,480),(1578.096,770)],[(230.256,1576),(690,1629),(1128.816,1860.624),(1578.096,1578)]]
GQ=[[(464,700),(904.176,649),(1354,649),(1550,1010)],[(464,1629),(904.176,1685),(1354,1685),(1550,1360)]]
for e in range(2):
 for c in range(4):
  stem=f'ge[{e}].gc[{c}].leaf';fq,gq=FQ[e][c],GQ[e][c]
  rq=(8.64+c*449.28+330,8.64+e*1391.04+469.584)
  for ctl,chunk in [('qv','rql_v'),('kv','rv')]+[(f'kkv[{k}]',f'rkv[{k}]')for k in range(4)]:
   fn=f'{stem}.f_{ctl}';gn=f'{stem}.g_{ctl}'
   if c==0:
    sn='qv_r'if ctl=='qv'else'bv_r'if ctl=='kv'else 'bi_r_and_nk_r_validity_comb'
    ff(fn,fq)
    sources=[sn]if ctl in ['qv','kv']else ['h_r']+[f'bi_r[{bb}]'for bb in range(8)]+[f'nk_r[{bb}]'for bb in range(12)]
    for ss in sources:arc(ss,fn,anchors[ss],fq,'quarter_to_first_leaf_control')
   regarc(fn,f'{stem}.core.{chunk}',fq,rq,'leaf_to_chunk_control')
   regarc(fn,gn,fq,gq,'leaf_control_f_to_g')
   if c<3:regarc(gn,f'ge[{e}].gc[{c+1}].leaf.f_{ctl}',gq,FQ[e][c+1],'control_next_leaf')
  # rql_v directly drives qv_b when QLATE=0; same common-core clock.
  qpin=P[0]['qv_b'];qsource=(8.64+c*449.28+qpin['x']+112.32,8.64+e*1391.04+469.584)
  # rql_v is independent from wide rq bits, choose its actual physical bank for all8 pins.
  anchors[f'{stem}.core.rql_v']=list(qsource)
  for r in arcs:
   if r['target']==f'{stem}.core.rql_v':
    r['target_um']=list(qsource);r['length_um']=round(l1(r['source_um'],qsource),6)
  for k in range(4):
   for hf in range(2):
    arc(f'{stem}.core.rql_v',f'e{e}c{c}k{k}h{hf}.qv_b',qsource,point('qv_b',e,c,k,hf),'rql_v_to_hcol')
    for j in range(32):
     # Native hid[4*hf+j//8][j%8] is shared across all four key columns.
     hn=f'{stem}.core.hid[{4*hf+j//8}][{j%8}]'
     hp=(8.64+c*449.28+hf*224.64+P[hf][f'hid4[{j}]']['x'],8.64+e*1391.04+469.584)
     ff(hn,hp);arc(hn,f'e{e}c{c}k{k}h{hf}.hid4[{j}]',hp,point(f'hid4[{j}]',e,c,k,hf),'native_hid_to_hcol')
  # Auxiliary/W-fault/metadata/keep use their own native banks in central street.
  for b in range(30):
   f=(200+c*449.28,1170);g=(424.64+c*449.28,1170)
   fn=f'{stem}.f_aux[{b}]';gn=f'{stem}.g_aux[{b}]'
   if c==0:
    ff(fn,f)
    srcs=(['ke_r']+[f'kb_r[{bb}]'for bb in range(171)]+[f'bi_r[{bb}]'for bb in range(8)])if b<4 else([]if b<8 else(['h_r']+[f'fo_r[{bb}]'for bb in range(11)]+[f'rk_r[{bb}]'for bb in range(7)]+[f'bi_r[{bb}]'for bb in range(8)]if b<28 else([f'bi_r[{bb}]'for bb in range(8)]+[f'nk_r[{bb}]'for bb in range(12)]if b==28 else ['bv_r','h_r']+[f'bi_r[{bb}]'for bb in range(8)]+[f'nk_r[{bb}]'for bb in range(12)]+[f'kl_r[{ll*1099+bb}]'for ll in range(4)for bb in range(11)])))
    for ss in srcs:arc(ss,fn,anchors[ss],f,'quarter_aux_to_leaf')
   regarc(fn,gn,f,g,'aux_f_to_g')
   if c<3:regarc(gn,f'ge[{e}].gc[{c+1}].leaf.f_aux[{b}]',g,(200+(c+1)*449.28,1170),'aux_next_leaf')
# Fix qv anchor rewrites and recompute failures at the end.
# The existing local readiness synchronizers: prdy -> rdy1 -> rdy2 -> online.
# Search only soft legal points; no extra online/relay FFs introduced.
xs=list(np.arange(12,1816,24))+[8.64+c*449.28+221.616 for c in range(4)]+[1812.096]
pts=np.array([(x,y)for x in xs for y in np.arange(12,2347,24)if free((x,y))])
for e in range(2):
 for c in range(4):
  stem=f'ge[{e}].gc[{c}].leaf.core';op=(8.64+c*449.28+221.616,8.64+e*1391.04+469.584);ff(stem+'.online',op)
  for k in range(4):
   for hf in range(2):
    for j in range(2):
     idx=4*k+2*hf+j;p=point(f'prdy[{j}]',e,c,k,hf);r1=(8.64+c*449.28+hf*224.64+W+3.024,p[1]);ff(f'{stem}.rdy1[{idx}]',r1)
     score=np.maximum(np.abs(pts-r1).sum(axis=1),np.abs(pts-op).sum(axis=1));r2=pts[np.argmin(score)].tolist()
     ff(f'{stem}.rdy2[{idx}]',r2);arc(f'e{e}c{c}k{k}h{hf}.prdy[{j}]',f'{stem}.rdy1[{idx}]',p,r1,'ready_first_capture');arc(f'{stem}.rdy1[{idx}]',f'{stem}.rdy2[{idx}]',r1,r2,'ready_second_capture');arc(f'{stem}.rdy2[{idx}]',stem+'.online',r2,op,'ready_reduce_online')
# u_vl D104 is native (LAT_T32 + FPL49 + XLAT23), five bits/chunk.
# Stage labels are logical source storage identities, not literal cell names.
for e in range(2):
 for c in range(4):
  stem=f'ge[{e}].gc[{c}].leaf.core';rp=(8.64+c*449.28+330,8.64+e*1391.04+469.584)
  for b in range(5):
   prev=stem+('.rv'if b==0 else f'.rkv[{b-1}]');pp=rp
   for st in range(104):
    nn=f'{stem}.u_vl.logical_stage[{st}][{b}]';np0=(230.256,478.224+e*1391.04)if c==0 and st==103 else rp
    regarc(prev,nn,pp,np0,'existing_chunk_valid_delay');prev,pp=nn,np0
# E-glue control consumers can sit near final g_qv/g_kv. Their fault_q/efault
# and wf_d feed the actual final fault checker within405 (no new relay stage).
for e in range(2):
 src=GQ[e][3];mid=(1550,1110 if e==0 else 1210)
 for name in ['fault_q','settle[0]','settle[1]']:
  regarc(f'ge[{e}].gc[3].leaf.g_qv',f'ge[{e}].{name}',src,mid,'E_glue_control_locality')
 for b in range(4):
  regarc(f'ge[{e}].ready1[{b}]',f'ge[{e}].ready2[{b}]',(1550,1170),(1550,1170),'E_glue_readiness')
  regarc(f'ge[{e}].ready2[{b}]',f'ge[{e}].online_q',(1550,1170),(1550,1170),'E_glue_readiness')
 regarc(f'ge[{e}].online_q',f'ge[{e}].fault_q',(1550,1170),mid,'E_glue_readiness')
 regarc(f'ge[{e}].fault_q','score_fault_check.fault',(1550,1110 if e==0 else 1210),(1550,1170),'fault_checker')
 # Actual keep D106 and metadata D123 pipeline banks; list exact stage counts,
 # not extra relays. Coordinates are bank anchors, not a packed register layout.
 for nm,width,depth in [('keep_pipe',4,106),('md',25,123)]:
  for b in range(width):
   prev=f'ge[{e}].gc[3].leaf.g_aux[{b if nm=="keep_pipe"else b+4}]';pp=(1772.48,1170)
   for st in range(depth):
    nn=f'ge[{e}].{nm}.line[{st}][{b}]';np0=(1500+(b%5)*12,1160+(b//5)*2)
    regarc(prev,nn,pp,np0,'existing_meta_keep_delay');prev,pp=nn,np0
# Complete the narrow scalar score-bus cuts using the same native b_w/e_bus
# staging as the scored sum/fault packet. Online occupies bit137; v bit136;
# kv bits132..135. No data storage is added by this coordinate model.
from collections import deque
adj=[np.flatnonzero(np.abs(pts-p).sum(axis=1)<=395).tolist()for p in pts]
tailpins=[{p['name']:p for p in json.load(open(D/f'pins_tail{e}.json'))}for e in range(2)]
def tpoint(e,name):
 p=tailpins[e][f'ge_{e}_u_t_{name}'];return [1581.12+p['x'],[950.4,1209.6][e]+(H-p['y']if e==0 else p['y'])]
def scalar_chain(e,c,busbit,src,sp,dst,dp):
 nh=2*(4-c)+1; dist=[999]*len(pts);parent={};q=deque();ends=np.flatnonzero(np.abs(pts-dp).sum(axis=1)<=395);starts=set(np.flatnonzero(np.abs(pts-sp).sum(axis=1)<=395).tolist());found=None
 for z in ends.tolist():dist[z]=1;q.append(z)
 while q:
  j=q.popleft()
  if j in starts:found=j;break
  if dist[j]>=nh-1:continue
  for z in adj[j]:
   if dist[z]==999:dist[z]=dist[j]+1;parent[z]=j;q.append(z)
 if found is None:bad.append(dict(kind='scalar_bus_no_native_slot_path',source=src,target=dst));return
 path=[];node=found
 while True:
  path.append(pts[node].tolist())
  if node not in parent:break
  node=parent[node]
 path=[path[0]]*(nh-1-len(path))+path
 names=[f'ge[{e}].gc[{cc}].leaf.{stage}[{c*138+busbit}]'for cc in range(c,4)for stage in['b_w','e_bus']]
 prev,pp=src,sp
 for nn,np0 in zip(names,path):ff(nn,np0);arc(prev,nn,pp,np0,'native_scalar_bus');prev,pp=nn,np0
 arc(prev,dst,pp,dp,'native_scalar_bus_consumer')
for e in range(2):
 for c in range(4):
  stem=f'ge[{e}].gc[{c}].leaf.core';op=anchors[stem+'.online']
  scalar_chain(e,c,137,stem+'.online',op,f'ge[{e}].ready1[{c}]',(1550,1170))
 # Tail consumes only sv/skv from slot0; other slots' copies are unconsumed.
 for b in range(5):
  src=f'ge[{e}].gc[0].leaf.core.u_vl.logical_stage[103][{b}]';sp=(230.256,478.224+e*1391.04);ff(src,sp)
  scalar_chain(e,0,136 if b==0 else 131+b,src,sp,f'ge[{e}].u_t.'+('i_v'if b==0 else f'i_kv[{b-1}]'),tpoint(e,'i_v'if b==0 else f'i_kv[{b-1}]'))
 for b in range(4):
  src=f'ge[{e}].keep_pipe.line[105][{b}]';arc(src,f'ge[{e}].u_t.i_keep[{b}]',anchors[src],tpoint(e,f'i_keep[{b}]'),'keep_actual_tail_pin')
 # Existing output pin flops: ov/ok/os/ofl followed by the quarter score flop.
 for port,width,regname,base in [('o_v',1,'ov',0),('o_kv',4,'ok',10+4*e),('o_score',64,'os',18+64*e),('o_fault',4,'ofl',2+4*e)]:
  for b in range(width):
   nm=port if width==1 else f'{port}[{b}]';p=tpoint(e,nm);rn=f'ge[{e}].{regname}'+(''if width==1 else f'[{b}]');rp=(1574,p[1]);ff(rn,rp)
   arc(f'ge[{e}].u_t.{nm}',rn,p,rp,'tail_output_pin_capture')
   sn='score_fault_check.fault'if port=='o_v'and e==1 else f'score[{base+b}]';ff(sn,(1550,1170));arc(rn,sn,rp,(1550,1170),'tail_capture_to_quarter_score')
 # Metadata arithmetic/OR adds no storage; map the exact score consumers.
 for b in range(25):
  src=f'ge[{e}].md.line[122][{b}]';sp=anchors[src]
  targets=([1]if e==0 else[])if b==24 else([2+4*e+b]if b<4 else[146+(4*e+l)*20+b-4 for l in range(4)])
  for sb in targets:ff(f'score[{sb}]',(1550,1170));arc(src,f'score[{sb}]',sp,(1550,1170),'metadata_to_actual_score')

# Canonical term geometry applies equally to soft FFs and hardmacro pins.
term_coords=collections.defaultdict(set)
for ar in arcs:
 for role in ['source','target']:term_coords[ar[role]].add(tuple(ar[role+'_um']))
coordinate_conflicts=[dict(identity=k,points=sorted(v))for k,v in term_coords.items()if len(v)>1]
# Check exact FF anchors against all hard bodies and report modeled coverage honestly.
bad=[r for r in bad if r.get('kind')=='scalar_bus_no_native_slot_path']+[r for r in arcs if r['length_um']>405+1e-6];illegal=[dict(identity=n,point_um=p)for n,p in anchors.items()if not free(p)]
cnt=collections.Counter(r['kind']for r in arcs);sums={k:dict(count=v,max_um=max(r['length_um']for r in arcs if r['kind']==k))for k,v in cnt.items()}
summary=dict(schema='opentallas.native_quarter_control_point_model.v1',source='ef994fe770',geometry_base='71648c3daf',added_cycles=0,extra_registers=0,arcs=sums,reach_failures=bad,illegal_anchors=illegal,coordinate_conflicts=coordinate_conflicts,modeled_ff=len(anchors),native_delay_depths=dict(keep_pipe=106,md=123,u_vl=104),identity_kind='SOURCE_LOGICAL_BANK_NOT_MAPPED_CELL',unclosed=['reset delivery source/geometry','full standard-cell packing with all data/output bays and PG/clock','W-glue and E-glue combinational setup/hold STA; actual logical delay stage→netlist register alias expansion','Native hid constants may synth-prune; anchor footprint conservative','Soft control logical-bank names need native mapped-netlist alias expansion; do not use as literal placement Tcl'],qualification='MODEL ONLY, not G1 or P&R acceptance; preserve existing native states')
json.dump(summary,open(a.out/'summary.json','w'),indent=2);json.dump(dict(arcs=arcs,anchors=anchors),open(a.out/'control_paths.json','w'),indent=2)
fig,ax=plt.subplots(figsize=(11,13))
for z in obs:
 x,y=z['origin_um'];w,h=z['outline_um'];ax.add_patch(Rectangle((x,y),w,h,fc='#ddd',ec='#777',lw=.3))
for r in arcs:
 if r['kind']in ['aux_f_to_g','aux_next_leaf','quarter_to_first_leaf_control','leaf_control_f_to_g','control_next_leaf','fault_checker']:
  x,y=r['source_um'];xx,yy=r['target_um'];ax.plot([x,xx],[y,yy],lw=.45,alpha=.25)
ax.set_xlim(0,1816.992);ax.set_ylim(0,2347.488);ax.set_aspect('equal');ax.set_title(f'Native quarter controls/meta point proposal; {len(bad)} reach failures / {len(illegal)} illegal anchors\nNo added stages; no physical packing or reset closure')
fig.savefig(a.out/'controls_meta.png',dpi=145,bbox_inches='tight')
print(json.dumps(dict(reach_failures=len(bad),illegal_anchors=len(illegal),coordinate_conflicts=len(coordinate_conflicts),arcs=sums)))
