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
 for i,b in enumerate(v['bits']):names[b].append(n+'['+str(i)+']')
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

summary=json.loads((p/'summary.json').read_text()); out=[]
for ix,chain in enumerate(summary['holding_candidates']):
 row={'index':ix,'depth':len(chain),'stages':[]}
 for name in chain:
  c=cells[name]; d=c['connections']['D'][0];q=c['connections']['Q'][0]
  row['stages'].append({'cell':name,'type':c['type'],'D':d,'Q':q,'Dnames':names[d],'Qnames':names[q],'clock':c['connections'].get('C'),'reset':c['connections'].get('R'),'Ddriver':drivers.get(d),'Qloads':ultimate(q),'attributes':c.get('attributes',{})})
 out.append(row)
Path('holding_enriched.json').write_text(json.dumps({'chains':out,'unconsumed':summary['unconsumed_FF']},indent=2)+'\n')
print('ENRICHED',len(out),sum(x['depth']for x in out))
