#!/usr/bin/env python3
"""Emit same-edge generic-RTL register/cone copies, never a Liberty FF model.

Clone equality assumes the common legal reset / first valid protocol. The
mapped native census, full-width behavioural bench and reset tests still gate
admission. No physical clock/reset or arbitrary-power-up claim is made here.
"""
import argparse,collections,copy,hashlib,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('input');p.add_argument('output');p.add_argument('--top',required=True);p.add_argument('--limit',type=int,default=24);a=p.parse_args()
raw=Path(a.input).read_bytes();j=json.loads(raw);m=j['modules'][a.top];cells=m['cells'];seqtypes={'$dff','$dffe','$adff','$adffe','$sdff','$sdffe','$sdffce'}
bit=max(b for c in cells.values()for bs in c['connections'].values()for b in bs if isinstance(b,int))+1
serial=0;ff_added=0;comb_added=0
newtop=a.top+'_native32'
def fresh(n=1):
 global bit
 z=list(range(bit,bit+n));bit+=n;return z
def param(n):return format(n,'032b')
def nextname(stem):
 global serial
 serial+=1;return 'safe32_'+stem+'_'+str(serial)
def keep(c):c.setdefault('attributes',{}).update(keep='1',dont_touch='1')
def emit_ff(c,indices,name):
 global ff_added
 z=copy.deepcopy(c);q=z['connections']['Q'];d=z['connections']['D'];w=int(z['parameters']['WIDTH'],2)
 z['connections']['Q']=fresh(len(indices));z['connections']['D']=[d[i]for i in indices];z['parameters']['WIDTH']=param(len(indices))
 for key in ['ARST_VALUE','SRST_VALUE']:
  if key in z['parameters']:
   old=z['parameters'][key][::-1];z['parameters'][key]=''.join(old[i]for i in indices)[::-1]
 keep(z);cells[name]=z;ff_added+=len(indices)
 for i,b in enumerate(z['connections']['Q']):m['netnames'][name+'_q'+str(i)]=dict(hide_name=0,bits=[b],attributes={'keep':'1','dont_touch':'1'})
 return z['connections']['Q']
# Vector control pins count once per physical FF, not once per RTL cell.
for name,c in list(cells.items()):
 if c['type']not in seqtypes:continue
 w=int(c['parameters']['WIDTH'],2)
 if w<=a.limit:continue
 del cells[name]
 for lo in range(0,w,a.limit):
  inds=list(range(lo,min(lo+a.limit,w)));z=copy.deepcopy(c);z['parameters']['WIDTH']=param(len(inds))
  for pin in ['D','Q']:z['connections'][pin]=[c['connections'][pin][i]for i in inds]
  for key in ['ARST_VALUE','SRST_VALUE']:
   if key in z['parameters']:z['parameters'][key]=c['parameters'][key][::-1][lo:lo+len(inds)][::-1]
  cells[name+'_part'+str(lo)]=z
# Mux select pins drive one gate/bit after mapping; split their datapaths too.
for name,c in list(cells.items()):
 if c['type']not in ['$mux','$pmux']:continue
 w=int(c['parameters']['WIDTH'],2)
 if w<=a.limit:continue
 del cells[name]
 sw=int(c['parameters'].get('S_WIDTH','1'),2)
 for lo in range(0,w,a.limit):
  count=min(a.limit,w-lo);z=copy.deepcopy(c);z['parameters']['WIDTH']=param(count)
  for pn in ['A','Y']:z['connections'][pn]=c['connections'][pn][lo:lo+count]
  z['connections']['B']=[b for k in range(sw)for b in c['connections']['B'][k*w+lo:k*w+lo+count]]
  cells[name+'_part'+str(lo)]=z
clocks={b for n,v in m['ports'].items()if n.startswith('ck_')for b in v['bits']}
def inventory():
 drivers={};users=collections.defaultdict(list);weights=collections.Counter()
 for n,c in cells.items():
  for pn,bs in c['connections'].items():
   dr=c['port_directions'][pn]
   if dr=='output':
    for i,b in enumerate(bs):
     if isinstance(b,int):drivers[b]=(n,pn,i)
   elif dr=='input'and pn.lower()not in ['clk','ck']:
    w=int(c['parameters'].get('WIDTH','1'),2)if ((c['type']in seqtypes and pn in ['ARST','SRST','EN'])or(c['type']in ['$mux','$pmux']and pn=='S'))else 1
    for i,b in enumerate(bs):
     if isinstance(b,int)and b not in clocks:users[b].append((n,pn,i,w));weights[b]+=w
 return drivers,users,weights
def clone_cone(b,drivers,memo):
 global comb_added
 if not isinstance(b,int)or b in clocks:return b
 if b in memo:return memo[b]
 if b not in drivers:raise RuntimeError('Cannot clone primary input cone bit '+str(b))
 n,pn,ix=drivers[b];c=cells[n]
 if c['type']in seqtypes:
  nb=emit_ff(c,[ix],nextname('ff'))[0];memo[b]=nb;return nb
 if c['type'].startswith('ot_sram'):raise RuntimeError('Cannot clone a macro output')
 z=copy.deepcopy(c);keep(z);name=nextname('logic')
 for po,bs in c['connections'].items():
  if c['port_directions'][po]=='output':
   new=fresh(len(bs));z['connections'][po]=new
   for old,nb in zip(bs,new):
    if isinstance(old,int):memo[old]=nb
 for pi,bs in c['connections'].items():
  if c['port_directions'][pi]=='input':z['connections'][pi]=[clone_cone(x,drivers,memo)for x in bs]
 cells[name]=z;comb_added+=1
 return memo[b]
rounds=0
while True:
 drivers,users,weights=inventory();bad=[(v,b)for b,v in weights.items()if v>a.limit]
 if not bad:break
 _,b=max(bad);entries=users[b]
 if b not in drivers:raise RuntimeError('Primary input exceeds limit '+str((b,weights[b])))
 groups=[];group=[];used=0
 for e in entries:
  if e[3]>a.limit:raise RuntimeError('Unsplit physical load '+str(e))
  if used+e[3]>a.limit:groups.append(group);group=[];used=0
  group.append(e);used+=e[3]
 if group:groups.append(group)
 for group in groups[1:]:
  nb=clone_cone(b,drivers,{})
  for cn,pn,ix,w in group:cells[cn]['connections'][pn][ix]=nb
 rounds+=1
 # Architectural reservation check, not a simulator/build timeout.
 if ff_added>2048:raise RuntimeError('Reprice model before exceeding2048 added control FF: '+str(ff_added))
j['modules'][newtop]=j['modules'].pop(a.top)
Path(a.output).write_text(json.dumps(j)+'\n')
record=dict(source_sha256=hashlib.sha256(raw).hexdigest(),top=newtop,limit=a.limit,rounds=rounds,added_ff_bits=ff_added,added_logic_cells=comb_added,largest_generic_weighted_load=max(weights.values()),clock_ports_unchanged=True,added_issue_edges=0,qualification='candidate only; native mapped32 + legalreset/fullprogramme proof required')
Path(a.output+'.record.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
