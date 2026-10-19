import collections,json,copy
from pathlib import Path
p=Path('control_census');design=json.loads((p/'netlist.json').read_text());m=copy.deepcopy(design['modules']['qfd_dv_lane_h_native_b64']);cells=m['cells']
nextbit=max(b for c in cells.values()for bs in c['connections'].values()for b in bs if isinstance(b,int))+1
while True:
 nested=[(n,c)for n,c in cells.items()if c['type']in design['modules']and not int(design['modules'][c['type']].get('attributes',{}).get('blackbox','0'),2)]
 if not nested:break
 for n,c in nested:
  sub=design['modules'][c['type']];mp={}
  for pn,pv in sub['ports'].items():
   for x,y in zip(pv['bits'],c['connections'][pn]):
    if isinstance(x,int):mp[x]=y
  for sc in sub['cells'].values():
   for bs in sc['connections'].values():
    for bit in bs:
     if isinstance(bit,int)and bit not in mp:mp[bit]=nextbit;nextbit+=1
  for nn,nv in sub['netnames'].items():
   for x in nv['bits']:
    if isinstance(x,int)and x not in mp:mp[x]=nextbit;nextbit+=1
   m['netnames'][n+'/'+nn]={'bits':[mp[x]if isinstance(x,int)else x for x in nv['bits']]}
  del cells[n]
  for sn,sc in sub['cells'].items():
   cc=copy.deepcopy(sc);cc['connections']={pn:[mp[x]if isinstance(x,int)else x for x in bs]for pn,bs in sc['connections'].items()};cells[n+'/'+sn]=cc
loads=collections.defaultdict(list);drivers={};names=collections.defaultdict(list)

for n,v in m['netnames'].items():
 for b in v['bits']:names[b].append(n)
for n,c in cells.items():
 for port,bits in c['connections'].items():
  for i,b in enumerate(bits):
   if c['port_directions'][port]=='input':loads[b].append((n,port,i))
   elif c['port_directions'][port]=='output':drivers[b]=(n,port,i)
for pn,pv in m['ports'].items():
 if pv['direction']=='output':
  for i,b in enumerate(pv['bits']):loads[b].append(('__port__/'+pn,'output',i))
def ultimate(b,seen=None):
 seen=set()if seen is None else seen
 if b in seen:return []
 seen.add(b);out=[]
 for n,port,i in loads[b]:
  if n not in cells:out.append((n,port,i));continue
  c=cells[n]
  if c['type'] in ('$_BUF_','$_NOT_'):
   for ob in c['connections']['Y']:out.extend(ultimate(ob,seen))
  else:out.append((n,port,i))
 return out
bad=[]
for b,d in drivers.items():
 u=ultimate(b)
 if len(u)>32:bad.append({'driver':d,'type':cells[d[0]]['type'],'bit':b,'names':names[b],'ultimate':len(u),'direct':len(loads[b]),'loads':u})
bad.sort(key=lambda x:-x['ultimate']);ff=[(n,c)for n,c in cells.items()if 'DFF'in c['type']];mac=collections.Counter(c['type']for c in cells.values()if 'sram'in c['type']);clks=collections.Counter(str(c['connections'].get('C'))for _,c in ff)
# Only plain unreset DFFs, sole D consumer on next identical clock: holding-only candidate.
nextff={};prev={}
for n,c in ff:
 if not c['type'].startswith('$_DFF_'):continue
 q=c['connections']['Q'][0];ul=ultimate(q)
 if len(ul)==1:
  nn,port,i=ul[0]
  if nn not in cells:continue
  cc=cells[nn]
  if port=='D'and cc['type'].startswith('$_DFF_')and cc['connections']['C']==c['connections']['C']:
   nextff[n]=nn;prev[nn]=n
chains=[]
for n in nextff:
 if n in prev:continue
 seq=[n];seen={n}
 while seq[-1]in nextff and nextff[seq[-1]]not in seen:
  seq.append(nextff[seq[-1]]);seen.add(seq[-1])
 if len(seq)>=3:chains.append(seq)
input_overloads=[{'port':pn,'index':i,'ultimate':len(ultimate(b))}for pn,pv in m['ports'].items()if pv['direction']=='input'and pn!='clk'for i,b in enumerate(pv['bits'])if len(ultimate(b))>32]
unconsumed_FF=[{'cell':n,'Q':c['connections']['Q'],'names':names[c['connections']['Q'][0]]}for n,c in ff if not ultimate(c['connections']['Q'][0])]
out={'unconsumed_FF':unconsumed_FF,'input_overloads':input_overloads,'cells':len(cells),'FF':len(ff),'macros':dict(mac),'clock_nets':dict(clks),'bad_drivers':bad,'holding_candidates':chains,'note':'Generic noabc source census; holding candidates require semantic audit, functional math stage flags may be useful. Reset and clock ancestry not physical qualified.'};(p/'summary.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items()if k not in('bad_drivers','holding_candidates','unconsumed_FF')},indent=2));print('unconsumed_FF',len(unconsumed_FF));print('bad_drivers',len(bad),'holding_candidates',len(chains));print(json.dumps([{k:v for k,v in x.items()if k!='loads'}for x in bad[:15]],indent=2))
