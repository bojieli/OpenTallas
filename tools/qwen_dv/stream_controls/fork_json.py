#!/usr/bin/env python3
"""Size/emit a scalar exact-equation consumer fork and explicit upstream API."""
import argparse,collections,copy,hashlib,json,pathlib
p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('--out',required=True);p.add_argument('--emit',action='store_true');a=p.parse_args()
raw=pathlib.Path(a.source).read_bytes();j=json.loads(raw);m=j['modules']['qfd_dv_stream_packer'];m=copy.deepcopy(m);base=copy.deepcopy(m['cells']);origin={k:k for k in base};aliases={};ports=[];limit=24
nextbit=1+max(b for n in m['netnames'].values() for b in n['bits'] if isinstance(b,int))
def net():
 global nextbit
 b=nextbit;nextbit+=1;return b
def eq(b):
 seen=set()
 while b in aliases:
  assert b not in seen;seen.add(b);b=aliases[b]
 return b
clock=set(m['ports']['ck']['bits'])
def graph():
 loads=collections.defaultdict(list);drivers={}
 for name,c in m['cells'].items():
  for pn,bs in c['connections'].items():
   for bi,b in enumerate(bs):
    if not isinstance(b,int):continue
    if c['port_directions'][pn]=='output':
     assert b not in drivers,(b,name,drivers.get(b));drivers[b]=(name,pn)
    else:loads[b].append((name,pn,bi))
 return loads,drivers
def transparent(c):return c['type'].startswith(('BUF','INV')) or c['type'] in ('$_BUF_','$_NOT_')
def ff(c):return c['type'].startswith(('$_DFF','$_SDFF','$_DFFE','DFF'))
loads,drivers=graph();before={b:len(ls) for b,ls in loads.items()};rounds=0
# First duplicate useful internal equations to a fixed point, including reset and D.
while True:
 rounds+=1;assert rounds<300,'copy fixed point did not converge'
 loads,drivers=graph();bad=[b for b,ls in loads.items() if b not in clock and b in drivers and len(ls)>(1 if transparent(m['cells'][drivers[b][0]]) else limit)]
 if not bad:break
 for b in bad:
  name,pn=drivers[b];c=m['cells'][name];assert all(len(bs)==1 for bs in c['connections'].values()),(name,'not scalar')
  cap=1 if transparent(c) else limit
  for n in range(1,(len(loads[b])+cap-1)//cap):
   cc=copy.deepcopy(c);newname='sc_copy_'+str(len(m['cells']));outs={}
   for op,bs in cc['connections'].items():
    if cc['port_directions'][op]=='output':
     nb=net();aliases[nb]=bs[0];outs[bs[0]]=nb;cc['connections'][op]=[nb]
   m['cells'][newname]=cc;origin[newname]=origin[name]
   for ln,lp,li in loads[b][n*cap:(n+1)*cap]:
    assert m['cells'][ln]['connections'][lp][li]==b
    m['cells'][ln]['connections'][lp][li]=outs[b]
# Expose each excess input group explicitly: actual predecessor copies required.
loads,drivers=graph()
for pn,pinfo in list(m['ports'].items()):
 if pinfo['direction']!='input' or pn=='ck':continue
 newbits=[]
 for bit,b in enumerate(pinfo['bits']):
  ls=loads.get(b,[])
  for n in range(1,(len(ls)+limit-1)//limit):
   nb=net();aliases[nb]=b;idx=len(newbits);newbits.append(nb)
   chosen=ls[n*limit:(n+1)*limit]
   ports.append({'port':pn+'_copies','copy_bit':idx,'source_port':pn,'source_bit':bit,'loads':len(chosen),'reset':pn=='rst_n'})
   for ln,lp,li in chosen:m['cells'][ln]['connections'][lp][li]=nb
 if newbits:m['ports'][pn+'_copies']={'direction':'input','bits':newbits}
# Every cell, including new state, has an original exact equation under source aliases.
for name,c in m['cells'].items():
 bc=base[origin[name]];assert c['type']==bc['type'] and c['parameters']==bc['parameters']
 for pn,bs in c['connections'].items():assert [eq(b) for b in bs]==bc['connections'][pn],(name,pn)
 c['attributes'].update({'keep':'1','dont_touch':'1'})
loads,drivers=graph();viol=[(b,len(ls)) for b,ls in loads.items() if b not in clock and len(ls)>32];assert not viol,viol
# One successor per transparent cell also bounds collapsed BUF/INV ultimate loads.
assert all(len(loads.get(b,[]))<=1 for b,(cn,_) in drivers.items() if transparent(m['cells'][cn]))
info={'source_sha256':hashlib.sha256(raw).hexdigest(),'source_top':'qfd_dv_stream_packer','candidate_top':'qfd_dv_stream_controls','limit':limit,'rounds':rounds,'before_cells':len(base),'after_cells':len(m['cells']),'before_ff':sum(ff(c) for c in base.values()),'after_ff':sum(ff(c) for c in m['cells'].values()),'clock_loads':sum(len(loads.get(b,[])) for b in clock),'max_nonclock_load':max(len(ls) for b,ls in loads.items() if b not in clock),'input_copy_counts':dict(collections.Counter(x['source_port'] for x in ports)),'added_edges':0,'equations_preserved':True,'qualified':False,'scope':'ABC native combinational cells; sequential primitives generic. Boundary copies require original-edge producer proof; no native clock/reset/physical qualification.'}
out=pathlib.Path(a.out);out.mkdir(parents=True,exist_ok=True);(out/'model.json').write_text(json.dumps(info,indent=2)+'\n');(out/'boundary.json').write_text(json.dumps(ports,indent=2)+'\n')
if a.emit:
 # Old named aliases can merge nets on re-import: keep only explicit port/cell wires.
 m['netnames']={};m['attributes']={'keep_hierarchy':'1'}
 j['modules'].pop('qfd_dv_stream_packer');j['modules']['qfd_dv_stream_controls']=m
 (out/'candidate.json').write_text(json.dumps(j)+'\n');(out/'correspondence.json').write_text(json.dumps({'origins':origin,'aliases':{str(k):v for k,v in aliases.items()},'equations_preserved':True,'source_sha256':info['source_sha256']})+'\n')
print(json.dumps(info,indent=2))
