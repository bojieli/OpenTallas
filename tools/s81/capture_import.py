#!/usr/bin/env python3
"""Opt-in, source-pinned capture expansion after buses_r8 and before hop repair.

The caller registers receipt bound_views/assigned_pins before finalization and
keeps the original hub geometric handle for planning. No RTL logic is created.
"""
from collections import defaultdict
from copy import deepcopy
import gzip
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PACKET = 'physical/s81_die_pins/capture_split_1016/source_current_binding.json.gz'

def _hash(path):
 return hashlib.sha256(path.read_bytes()).hexdigest()

def _slice(port, width):
 match=re.fullmatch(r'([^\[\]@]+)(?:\[(\d+)(?::(\d+))?\])?',port)
 if not match: raise ValueError('unsupported endpoint slice '+port)
 base,a,b=match.groups()
 if a is None: return base,list(range(width))
 lo=int(a);hi=int(b) if b is not None else lo
 if hi<lo or hi-lo+1!=width: raise ValueError('endpoint width/slice mismatch '+port)
 return base,list(range(lo,hi+1))

def _pin_slice(pin):
 match=re.fullmatch(r'(.*)\[(\d+)\]',pin)
 return f'{match[1]}[{match[2]}:{match[2]}]' if match else pin

def _load(packet, root):
 if isinstance(packet,dict): data=deepcopy(packet); packet_sha=None
 else:
  path=Path(packet); path=path if path.is_absolute() else root/path
  raw=path.read_bytes(); packet_sha=hashlib.sha256(raw).hexdigest()
  data=json.loads(gzip.decompress(raw) if path.suffix=='.gz' else raw)
 if data.get('schema')!='opentallas.s81.capture_source_binding.v1': raise ValueError('unsupported capture packet schema')
 for path,digest in data['source_sha256'].items():
  file=root/path
  if not file.is_file() or _hash(file)!=digest: raise ValueError('capture source hash mismatch '+path)
 for master,v in data['views'].items():
  for path,digest in v['sha256'].items():
   file=root/path
   if not file.is_file() or _hash(file)!=digest: raise ValueError('capture view hash mismatch '+path)
  if not v.get('native_audit',{}).get('pass'): raise ValueError('capture master native audit absent/failing '+master)
 if data['counts']['literal_clock_contacts']!=86 or len(data['children'])!=70: raise ValueError('capture packet shape mismatch')
 return data,packet_sha

def expand(m, parent_name='sp_capture', packet=DEFAULT_PACKET, *, root=ROOT, inst_ctor=None):
 """Atomically replace parent buses and instance by actual packet hard leaves.

 Generic ck/ckv endpoints broadcast to the packet's stream/serial clock bits.
 All other parent ports must match exactly; no missing data/reset/clock bits
 are tolerated. Return assigned LEF contacts, view bindings and clock targets.
 Parent geometry remains in m['hub']; only m['insts']/m['buses'] are replaced.
 """
 root=Path(root);data,digest=_load(packet,root)
 parents=[i for i in m['insts'] if i.name==parent_name]
 if len(parents)!=1: raise ValueError('capture import requires one parent '+parent_name)
 parent=parents[0]
 if parent.orient not in ('R0','MY'): raise ValueError('capture parent orientation '+parent.orient)
 if any(parent_name+'__' in i.name for i in m['insts']): raise ValueError('capture already expanded/name collision')
 pw,ph=data['outline_um']
 if abs(parent.w-pw)>0.001 or abs(parent.h-ph)>0.001: raise ValueError('capture parent outline differs from packet')
 ctor=inst_ctor or type(parent)
 names={n:parent_name+'__'+re.sub(r'[^A-Za-z0-9_]', '_',n) for n in data['children']}
 if len(set(names.values()))!=len(names): raise ValueError('capture leaf name collision')
 children=[];assigned={};bound={};clocks=[];real_ports={};pin_tables={}
 for n,c in data['children'].items():
  if c.get('orient') != 'R0': raise ValueError('capture packet local orientation must be R0: '+n)
  x,y=c['at_um'];w,h=c['outline_um'];orient=parent.orient
  x=parent.x+(pw-x-w if orient=='MY' else x);y=parent.y+y
  domains={e['domain'] for e in data['clock_entries'] if e['child']==n}
  if len(domains)!=1: raise ValueError('capture leaf domain ambiguous '+n)
  domain='serial_0p9' if domains=={'serial'} else 'stream_1p2'
  children.append(ctor(names[n],c['master'],x,y,w,h,orient=orient,kind='capture_leaf',region=parent.region,domain=domain))
  for pin,p in c['pins'].items():
   lx,ly=p['local_xy_um'];assigned[names[n]+'/'+pin]={'layer':p['layer'],'local_xy_um':[lx,ly],'xy_um':[x+(w-lx if orient=='MY' else lx),y+ly]}
  v=data['views'][c['master']];view=Path(v['view']);mst=c['master']
  rp=defaultdict(list)
  for pin,p in c['pins'].items():rp[pin.split('[')[0]].append(pin)
  real_ports[mst]={base:sorted(pins,key=lambda p:int(p.split('[')[1][:-1]) if '[' in p else -1) for base,pins in rp.items()}
  pin_tables[mst]={pin:{'layer':p['layer'],'local_xy_um':p['local_xy_um'],'direction':p['direction']} for pin,p in c['pins'].items()}
  bound[mst]={'lef':str(view/(mst+'.lef')),'ss':str(view/(mst+'_ss.lib')),'ff':str(view/(mst+'_ff.lib')),'tt':str(view/(mst+'_tt.lib')),'insertion':str(view/'insertion.json'),'w':w,'h':h,'verdict':'DIAGNOSTIC_CLOSED','binding_scope':'SOURCE_CURRENT_CAPTURE_IMPORT_DIE_QUALIFICATION_PENDING','sha256':v['sha256'],'native_audit':v['native_audit']}
 for e in data['clock_entries']:
  item=deepcopy(e);item['source_child']=item['child'];item['child']=names[item['child']];item['xy_um']=assigned[item['child']+'/'+item['pin']]['xy_um'];clocks.append(item)
 # Packet bit identity is authoritative. Every external bit net absorbs all
 # internal contacts on that bit, so one output pin never drives two nets.
 ports=data['die_ports'];by_port=defaultdict(dict)
 for pin,p in ports.items():
  base,ix=_slice(pin,1);by_port[base][ix[0]]=p
 def selections(port,width):
  base,indices=_slice(port,width)
  if base in ('ck','ckv') and base not in by_port:
   if width!=1:raise ValueError('generic capture clock must be scalar '+port)
   keys=[p for p in ports if p.startswith('ckv')== (base=='ckv') and p.startswith('ck')]
   return [[ports[p] for p in keys]]
  if base not in by_port:raise ValueError('unknown capture parent port '+port)
  if any(i not in by_port[base] for i in indices):raise ValueError('missing capture parent bit '+port)
  return [[by_port[base][i]] for i in indices]
 def contacts(records):
  result=[]
  for rec in records:
   for e in rec['contacts']:
    ep=(names[e['child']],_pin_slice(e['pin']))
    if ep not in result:result.append(ep)
  return result
 buses=[];covered=set();external_bits=set();bit_bus={}
 for bus in m['buses']:
  bid,cls,width,eps,*tail=bus
  hits=[(j,p) for j,(n,p) in enumerate(eps) if n==parent_name]
  if not hits:buses.append(bus);continue
  if len(hits)>1:
   # buses_r8 puts each logical tile clock entry on a shared scalar trunk.
   # Expand every input endpoint together, retaining that one original net.
   records=[];categories=set()
   for _,port in hits:
    base,_=_slice(port,width)
    category='serial' if base.startswith('ckv') else 'stream' if base.startswith('ck') else base
    if width!=1 or category not in ('stream','serial','rst','rsv'):
     raise ValueError('multiple capture data endpoints on one bus '+bid)
    categories.add(category)
    chosen=selections(port,width)[0]
    if any(r['direction']!='input' for r in chosen):
     raise ValueError('shared capture net contains output '+bid)
    records.extend(chosen)
   if len(categories)!=1:raise ValueError('mixed capture clock/reset domains on one bus '+bid)
   replacement=contacts(records)
   if not replacement:raise ValueError('empty shared capture net '+bid)
   ordered=[];inserted=False
   for n,p in eps:
    if n==parent_name:
     if not inserted:ordered.extend(replacement);inserted=True
    else:ordered.append((n,p))
   ordered=list(dict.fromkeys(ordered))
   logical_bits={r['bit'] for r in records}
   if logical_bits & external_bits:raise ValueError('capture clock/reset bit appears on multiple nets '+bid)
   for bit in logical_bits:bit_bus[bit]=len(buses)
   covered.update(logical_bits);external_bits.update(logical_bits)
   buses.append((bid,cls,width,ordered,*tail))
   continue
  pos,port=hits[0];selected=selections(port,width)
  peer_bits=[]
  for j,(n,p) in enumerate(eps):
   if j!=pos:
    if '@' in p:
     body,off=p.rsplit('@',1);off=int(off)
     mm=re.search(r'\[(\d+)(?::(\d+))?\]$',body)
     if not mm:raise ValueError('partial peer requires explicit slice '+p)
     length=int(mm[2] or mm[1])-int(mm[1])+1;base,ix=_slice(body,length)
     indices={off+k:v for k,v in enumerate(ix)}
     if off+length>width:raise ValueError('partial peer exceeds net '+p)
    else:
     base,ix=_slice(p,width);indices=dict(enumerate(ix))
    peer_bits.append((j,n,base,indices))
  for i,records in enumerate(selected):
   covered.update(r['bit'] for r in records);external_bits.update(r['bit'] for r in records)
   replacement=contacts(records)
   if not replacement:raise ValueError('empty capture contact '+port)
   # Inputs need external driver first, outputs their one actual leaf driver.
   ordered=[]
   for j,(n,p) in enumerate(eps):
    if j==pos:ordered.extend(replacement)
    else:
     _,_,base,indices=next(q for q in peer_bits if q[0]==j)
     # Preserve scalar endpoint spellings; explicit slices are needed for buses.
     if i in indices:ordered.append((n,base if width==1 and '[' not in p else f'{base}[{indices[i]}:{indices[i]}]'))
   records_out=[r for r in records if r['direction']=='output']
   if records_out:
    drivers=[(names[e['child']],_pin_slice(e['pin'])) for r in records_out for e in r['contacts'] if e['direction']=='output']
    if len(set(drivers))!=1:raise ValueError('capture output lacks one driver '+port)
    ordered=list(dict.fromkeys(drivers+ordered))
   if len(records)==1 and records[0]['bit'] in bit_bus:
    old=bit_bus[records[0]['bit']]; prior=buses[old]; buses[old]=(*prior[:3],list(dict.fromkeys(prior[3]+ordered)),*prior[4:])
   else:
    if len(records)==1:bit_bus[records[0]['bit']]=len(buses)
    buses.append((bid if width==1 else f'{bid}__captbit{i}',cls,1,ordered,*tail))
 expected={p['bit'] for p in ports.values()}
 if covered!=expected:raise ValueError('unbound capture external bits '+str(sorted(expected-covered)[:20]))
 # All remaining graph bits become one-driver physical leaf-to-leaf nets.
 internal=defaultdict(dict)
 for n,c in data['children'].items():
  for pin,p in c['pins'].items():
   if p['bit'] not in external_bits:internal[p['bit']][(names[n],_pin_slice(pin))]=p['direction']
 for bit,es in internal.items():
  ds=[ep for ep,d in es.items() if d=='output'];ss=[ep for ep,d in es.items() if d=='input']
  if len(ds)!=1 or not ss:raise ValueError('invalid capture internal net '+str(bit))
  buses.append((f'{parent_name}__internal_{bit}','capture_internal',1,ds+ss))
 receipt={'schema':'opentallas.s81.capture_model_import.v1','packet_sha256':digest,'parent':parent_name,'orientation':parent.orient,'children':names,'bound_views':bound,'real_ports':real_ports,'master_pin_tables':pin_tables,'assigned_pins':assigned,'clock_entries':clocks,'counts':{'children':len(children),'masters':len(bound),'literal_clock_contacts':len(clocks),'external_bits':len(covered),'internal_nets':len(internal)},'parent_geometry':parent.d()}
 receipt['native_leaf_signature']={names[n]:{'master':c['master'],'outline_um':c['outline_um'],'orient':parent.orient} for n,c in data['children'].items()}
 receipt['native_internal_edges']=[[(names[p['driver'].rsplit('/',1)[0]],p['driver'].rsplit('/',1)[1]),(names[p['sink'].rsplit('/',1)[0]],p['sink'].rsplit('/',1)[1])] for p in data['internal_paths']]
 receipt['fixed_internal_nets']=[list(b[3]) for b in buses if b[1]=='capture_internal']
 # No mutation occurs before all source, connectivity and geometry checks pass.
 m['insts']=[it for it in m['insts'] if it.name!=parent_name]+children
 m['buses']=buses
 m['capture_import']=receipt
 for cache in ('pdir','_by','_nets_of','_nets_of_o'):m.pop(cache,None)
 return receipt


def validate_native_connectivity(m):
 """Reject calendar-changing stages, altered masters or extra internal consumers.

 Timing checks remain responsible for every join. Generic transport repair may
 not change a hardened, source-proven composition's internal register ages.
 """
 r=m.get('capture_import')
 if not r:return
 def canon(ep):
  name,pin=ep
  match=re.fullmatch(r'(.*)\[(\d+):(\d+)\]',pin)
  if match and match[2]==match[3]:pin=f'{match[1]}[{match[2]}]'
  return name,pin
 by={it.name:it for it in m['insts']}
 for name,expected in r['native_leaf_signature'].items():
  it=by.get(name)
  if it is None or it.master!=expected['master'] or it.orient!=expected['orient'] or any(abs(a-b)>1e-6 for a,b in zip((it.w,it.h),expected['outline_um'])):
   raise ValueError('capture native leaf changed outside its source contract: '+name)
 nets=[];of=defaultdict(set)
 for bid,cls,width,eps,*tail in m['buses']:
  native=[ep for ep in eps if ep[0] in r['native_leaf_signature']]
  if not native:continue
  if width!=1:raise ValueError('capture native bit was combined into a different-width net: '+bid)
  key=len(nets);points={canon(ep) for ep in eps};nets.append(points)
  for ep in native:of[canon(ep)].add(key)
 for source,sink in r['native_internal_edges']:
  if not (of[canon(source)] & of[canon(sink)]):
   raise ValueError('capture internal fixed-cycle edge retimed or disconnected: '+str((source,sink)))
 for expected in r['fixed_internal_nets']:
  points={canon(ep) for ep in expected};first=next(iter(points))
  if len(of[first])!=1 or nets[next(iter(of[first]))]!=points:
   raise ValueError('capture internal stage or extra consumer inserted: '+str(first))
 r['fixed_cycle_connectivity']='PASS exact native internal graph; no added stages'
