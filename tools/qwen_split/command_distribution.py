"""Balanced source-bound static command fanout for the six b2 train consumers.

Branches use actual independent registered output ports. All field links at a
level share an allocator equal-age group. There are no runtime ready/credit
signals. Candidate homes/pins require fresh CTS/native and die routing proof.
"""
import copy,hashlib,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
MASTER='qfd_static_command_fork42'
SOURCE='rtl/qwen_split/qfd_static_command_fork42.sv'
FIELDS=(('train_start',1),('train_count',4),('capture_stride',32),('payload_write',1),('slot_count',4))
WH=(43.2,43.2)

def joins():
 out={};offset=0
 for field,n in FIELDS:
  for real in ('a','b0','b1'):out[f'{real}_{field}']=(real,list(range(offset,offset+n)))
  offset+=n
 assert offset==42
 return out

def apply(model,sinks,issuer='res_train_issue'):
 by={i.name:i for i in model['insts']}
 if len(sinks)!=len(set(sinks))or len(sinks)<2 or not set(sinks)<=set(by):
  raise ValueError('command tree requires distinct existing consumers')
 source=by[issuer];prototype=copy.copy(source)
 fields={p:n for p,n in FIELDS};found={};keep=[]
 for bid,cl,n,es in model['buses']:
  if es and es[0][0]==issuer and es[0][1]in fields and cl not in('clock_trunk','reset'):
   field=es[0][1]
   if field in found or n!=fields[field]or {i for i,p in es[1:]}!=set(sinks)or any(p!=field for i,p in es[1:]):
    raise ValueError(f'{bid}: command source must cover exactly current consumers at real field width')
   found[field]=bid
  else:keep.append((bid,cl,n,es))
 if set(found)!=set(fields):raise ValueError(f'missing commands {set(fields)-set(found)}')
 clock=[b for b in keep if b[1]=='clock_trunk'and(issuer,'ck')in b[3]]
 reset=[b for b in keep if b[1]=='reset'and(issuer,'rst_n')in b[3]]
 if len(clock)!=1 or len(reset)!=1:raise ValueError('need exact issuer clock and reset roots')
 depth=math.ceil(math.log2(len(sinks)));nodes=[];edges=[];obs=list(model['insts']);groups={}
 def free_home(cx,cy):
  w,h=WH
  for ring in range(200):
   for dy in range(-ring,ring+1):
    for dx in ({-ring,ring}if abs(dy)<ring else range(-ring,ring+1)):
     x=round(round((cx-w/2+dx*10.8)/2.16)*2.16,3)
     y=round(round((cy-h/2+dy*10.8)/2.16)*2.16,3)
     if min(x,y)<0 or x+w>model['die']['w']or y+h>model['die']['h']:continue
     if any(i.x<x+w and i.x+i.w>x and i.y<y+h and i.y+i.h>y for i in obs):continue
     return x,y
  raise ValueError('no free registered command fork home')
 def build(dest,level,parent=None,branch=None):
  node=copy.copy(prototype);node.name=f'command_fork_{len(nodes)}';node.master=MASTER
  node.w,node.h=WH;node.orient='R0';node.kind='command_fork'
  if parent is None:cx,cy=source.x+source.w+WH[0]/2+21.6,source.y+source.h/2
  else:
   dcx=sum(by[n].x+by[n].w/2 for n in dest)/len(dest)
   dcy=sum(by[n].y+by[n].h/2 for n in dest)/len(dest)
   cx=(parent.x+parent.w/2+dcx)/2;cy=(parent.y+parent.h/2+dcy)/2
  node.x,node.y=free_home(cx,cy);nodes.append(node);obs.append(node)
  for f,n in FIELDS:
   bid=f'cmd_l{level}_{node.name}_{f}'
   src=(issuer,f)if parent is None else(parent.name,f'b{branch}_{f}')
   edges.append((bid,'spine_local',n,[src,(node.name,'a_'+f)]))
   groups.setdefault(f'command_level_{level}',[]).append(bid)
  if level==depth-1:
   if len(dest)>2:raise ValueError('internal command depth mismatch')
   for br,target in enumerate(dest):
    for f,n in FIELDS:
     bid=f'cmd_leaf_{target}_{f}'
     edges.append((bid,'spine_local',n,[(node.name,f'b{br}_{f}'),(target,f)]))
     groups.setdefault(f'command_level_{depth}',[]).append(bid)
  else:
   cut=(len(dest)+1)//2
   build(dest[:cut],level+1,node,0)
   if dest[cut:]:build(dest[cut:],level+1,node,1)
 build(sorted(sinks,key=lambda n:(by[n].x,by[n].y)),0)
 for j,(bid,cl,n,es)in enumerate(keep):
  if bid==clock[0][0]:keep[j]=(bid,cl,n,list(es)+[(i.name,'ck')for i in nodes])
  if bid==reset[0][0]:keep[j]=(bid,cl,n,list(es)+[(i.name,'rst_n')for i in nodes])
 model['insts']+=nodes;model['buses']=keep+edges
 model.setdefault('port_join',{})[MASTER]=joins()
 model.setdefault('relay_equal_groups',{}).update(groups)
 rec=dict(master=MASTER,source=SOURCE,source_sha256=hashlib.sha256((ROOT/SOURCE).read_bytes()).hexdigest(),
  fields=list(FIELDS),clock_net=clock[0][0],reset_net=reset[0][0],normal_logic_edges=depth,
  cold_reset_release_extra_edges=1,nodes=[dict(name=i.name,x=i.x,y=i.y,w=i.w,h=i.h)for i in nodes],
  sinks=list(sinks),equal_groups=groups,retired_unrelayed_fanouts=found,
  clock_contract='one compensated clock entry per fork, phi minus measured insertion; actual CTS pending',
  compiled_latency='depth logic edges plus actual allocator stage_of per level, assert equal fields and consumers',
  qualification=False)
 model['command_distribution']=rec;return rec

def install_master(M,model,Master,pin_rects):
 if 'command_distribution'not in model:return
 from qwen_split.source_pin_plan import rtl_ports,snap
 from qwen_split.direct_up4 import partition_master
 pp=rtl_ports(ROOT/SOURCE,MASTER)
 expected=dict(ck=(1,'input'),rst_n=(1,'input'),a=(42,'input'),b0=(42,'output'),b1=(42,'output'))
 if pp!=expected:raise ValueError('command fork source ABI mismatch')
 q=Master(MASTER,*WH,5,'NEW source-bound registered static command fork,85 FF, no physical inheritance')
 q.ports={
  'a':('pins',42,'W','M4',[snap(19.632+k*.096)for k in range(42)],1),
  'b0':('pins',42,'E','M4',[snap(19.632+k*.096)for k in range(42)],1),
  'b1':('pins',42,'N','M5',[snap(19.632+k*.096)for k in range(42)],1),
  'ck':('pins',1,'N','M5',[snap(10.8)],1),
  'rst_n':('pins',1,'N','M5',[snap(12.96)],1)}
 q.order=list(q.ports)
 rects=pin_rects(q,1,{p:sp[1]for p,sp in q.ports.items()})
 partition_master(q,joins(),rects);M[MASTER]=q
