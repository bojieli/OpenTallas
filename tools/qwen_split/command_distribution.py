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
WH=(17.28,15.12)
SHAPES={'qfd_static_command_fork42':WH,'qfd_static_selector_fork26':(15.12,12.96),'qfd_static_selector_fork4':(12.96,10.8)}

def joins(fielddefs=FIELDS):
 out={};offset=0
 for field,n in fielddefs:
  for real in ('a','b0','b1'):out[f'{real}_{field}']=(real,list(range(offset,offset+n)))
  offset+=n
 return out

def apply(model,sinks,issuer='res_train_issue',fielddefs=FIELDS,master=MASTER,source_file=SOURCE,prefix='command',clock_port='ck',reset_port='rst_n'):
 by={i.name:i for i in model['insts']}
 if len(sinks)!=len(set(sinks))or len(sinks)<2 or not set(sinks)<=set(by):
  raise ValueError('command tree requires distinct existing consumers')
 source=by[issuer];prototype=copy.copy(source)
 fields={p:n for p,n in fielddefs};found={};keep=[]
 for bid,cl,n,es in model['buses']:
  if es and es[0][0]==issuer and es[0][1]in fields and cl not in('clock_trunk','reset'):
   field=es[0][1]
   if field in found or n!=fields[field]or {i for i,p in es[1:]}!=set(sinks)or any(p!=field for i,p in es[1:]):
    raise ValueError(f'{bid}: command source must cover exactly current consumers at real field width')
   found[field]=bid
  else:keep.append((bid,cl,n,es))
 if set(found)!=set(fields):raise ValueError(f'missing commands {set(fields)-set(found)}')
 clock=[b for b in keep if b[1]=='clock_trunk'and(issuer,clock_port)in b[3]]
 reset=[b for b in keep if b[1]=='reset'and(issuer,reset_port)in b[3]]
 if len(clock)!=1 or len(reset)!=1:raise ValueError('need exact issuer clock and reset roots')
 depth=math.ceil(math.log2(len(sinks)));nodes=[];edges=[];obs=list(model['insts']);groups={}
 def free_home(cx,cy):
  w,h=SHAPES.get(master,WH)
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
  node=copy.copy(prototype);node.name=f'{prefix}_fork_{len(nodes)}';node.master=master
  node.w,node.h=SHAPES.get(master,WH);node.orient='R0';node.kind='command_fork'
  if parent is None:cx,cy=source.x+source.w+WH[0]/2+21.6,source.y+source.h/2
  else:
   dcx=sum(by[n].x+by[n].w/2 for n in dest)/len(dest)
   dcy=sum(by[n].y+by[n].h/2 for n in dest)/len(dest)
   cx=(parent.x+parent.w/2+dcx)/2;cy=(parent.y+parent.h/2+dcy)/2
  node.x,node.y=free_home(cx,cy);nodes.append(node);obs.append(node)
  for f,n in fielddefs:
   bid=f'{prefix}_l{level}_{node.name}_{f}'
   src=(issuer,f)if parent is None else(parent.name,f'b{branch}_{f}')
   edges.append((bid,'spine_local',n,[src,(node.name,'a_'+f)]))
   groups.setdefault(f'{prefix}_level_{level}',[]).append(bid)
  if level==depth-1:
   if len(dest)>2:raise ValueError('internal command depth mismatch')
   for br,target in enumerate(dest):
    for f,n in fielddefs:
     bid=f'{prefix}_leaf_{target}_{f}'
     edges.append((bid,'spine_local',n,[(node.name,f'b{br}_{f}'),(target,f)]))
     groups.setdefault(f'{prefix}_level_{depth}',[]).append(bid)
  else:
   cut=(len(dest)+1)//2
   build(dest[:cut],level+1,node,0)
   if dest[cut:]:build(dest[cut:],level+1,node,1)
 build(sorted(sinks,key=lambda n:(by[n].x,by[n].y)),0)
 for j,(bid,cl,n,es)in enumerate(keep):
  if bid==clock[0][0]:keep[j]=(bid,cl,n,list(es)+[(i.name,'ck')for i in nodes])
  if bid==reset[0][0]:keep[j]=(bid,cl,n,list(es)+[(i.name,'rst_n')for i in nodes])
 model['insts']+=nodes;model['buses']=keep+edges
 model.setdefault('port_join',{})[master]=joins(fielddefs)
 model.setdefault('relay_equal_groups',{}).update(groups)
 rec=dict(master=master,source=source_file,source_sha256=hashlib.sha256((ROOT/source_file).read_bytes()).hexdigest(),
  fields=list(fielddefs),clock_net=clock[0][0],reset_net=reset[0][0],normal_logic_edges=depth,
  cold_reset_release_extra_edges=1,nodes=[dict(name=i.name,x=i.x,y=i.y,w=i.w,h=i.h)for i in nodes],
  sinks=list(sinks),equal_groups=groups,retired_unrelayed_fanouts=found,
  clock_contract='one compensated clock entry per fork, phi minus measured insertion; actual CTS pending',
  compiled_latency='sum actual stage_of per level includes fork register edges and final consumer capture; added vs direct = depth plus sum(stage_of minus1); assert equal fields/consumers',
  qualification=False)
 model.setdefault('distribution_trees',{})[prefix]=rec
 if prefix=='command':model['command_distribution']=rec
 return rec

def install_master(M,model,Master,pin_rects):
 trees=model.get('distribution_trees',{})
 if not trees and model.get('command_distribution'):trees={'command':model['command_distribution']}
 if not trees:return
 from qwen_split.source_pin_plan import rtl_ports,snap
 from qwen_split.direct_up4 import partition_master
 for rec in trees.values():
  mn=rec['master'];fd=rec['fields'];width=sum(n for f,n in fd)
  pp=rtl_ports(ROOT/rec['source'],mn)
  expected=dict(ck=(1,'input'),rst_n=(1,'input'),a=(width,'input'),b0=(width,'output'),b1=(width,'output'))
  if pp!=expected:raise ValueError(f'{mn} fork source ABI mismatch')
  ww,hh=SHAPES.get(mn,WH)
  q=Master(mn,ww,hh,5,f'NEW source-bound registered static fork,{2*width+1} FF, no physical inheritance')
  side=[snap(2.16+k*(hh-4.32)/(width-1))for k in range(width)]
  north=[snap(3.42+k*(ww-5.58)/(width-1))for k in range(width)]
  q.ports={
   'a':('pins',width,'W','M4',side,1),
   'b0':('pins',width,'E','M4',side,1),
   'b1':('pins',width,'N','M5',north,1),
   'ck':('pins',1,'N','M5',[snap(1.08)],1),
   'rst_n':('pins',1,'N','M5',[snap(2.16)],1)}
  q.order=list(q.ports)
  rects=pin_rects(q,1,{p:sp[1]for p,sp in q.ports.items()})
  partition_master(q,joins(fd),rects);M[mn]=q
