"""Geometric PG conductor union, without net-name connectivity shortcuts."""
import gzip,json,collections,hashlib,re
from pathlib import Path
P=Path('.')
with gzip.open('metal.json.gz','rt') as f:j=json.load(f)
s=j['shapes']; n=len(s); par=list(range(n));sz=[1]*n
find=lambda x:x
def root(x):
 while par[x]!=x:par[x]=par[par[x]];x=par[x]
 return x
def join(a,b):
 a,b=root(a),root(b)
 if a==b:return
 if sz[a]<sz[b]:a,b=b,a
 par[b]=a;sz[a]+=sz[b]
def touch(a,b):return a[0]<=b[2] and b[0]<=a[2] and a[1]<=b[3] and b[1]<=a[3]
def area_overlap(a,b):return a[0]<b[2] and b[0]<a[2] and a[1]<b[3] and b[1]<a[3]
grid=collections.defaultdict(list);step=1000;shorts=[];grid_bad=[]
for idx,(lay,box,role,owner) in enumerate(s):
 if any(c % j['grid'] for c in box):grid_bad.append(idx)
 if j['layers'][lay]['type']!='ROUTING':continue
 x0,y0,x1,y1=[v//step for v in box];seen=set()
 for x in range(x0,x1+1):
  for y in range(y0,y1+1):
   key=(lay,x,y)
   for other in grid[key]:
    if other in seen:continue
    seen.add(other)
    if touch(box,s[other][1]):
     if role!=s[other][2]:shorts.append([idx,other])
     join(idx,other)
   grid[key].append(idx)
via_bad=[]; cuts=0
for v in j['vias']:
 metals=[i for i in v['ids'] if j['layers'][s[i][0]]['type']=='ROUTING']
 cs=[i for i in v['ids'] if j['layers'][s[i][0]]['type']=='CUT']
 for c in cs:
  hits=[i for i in metals if (s[i][1][0]<=s[c][1][0] and s[i][1][1]<=s[c][1][1] and s[i][1][2]>=s[c][1][2] and s[i][1][3]>=s[c][1][3])]
  if len({s[i][0] for i in hits})!=2:via_bad.append({'via':v,'cut':c,'hits':hits})
  else:
   for h in hits:join(c,h)
  cuts+=1
seeds=collections.defaultdict(set)
for t in j['bterms']:
 for i in t['ids']:seeds[t['role']].add(root(i))
missing=[]; ambiguous=[]
for p in j['pins']:
 rr={root(i) for i in p['ids']}
 if not rr or not rr<=seeds[p['role']]:missing.append({**p,'components':sorted(rr)})
 if rr & seeds['GROUND' if p['role']=='POWER' else 'POWER']:ambiguous.append(p)
result={'schema':'opentallas.pg_conductor_readonly.v1','shapes':n,'via_instances':len(j['vias']),'cuts_checked':cuts,'grid_dbu':j['grid'],'grid_offenders':grid_bad,'via_enclosure_contact_failures':via_bad,'vdd_vss_same_layer_shorts':shorts,'pg_terminal_count':len(j['pins']),'pg_terminals_not_entirely_connected_to_matching_supply_bpins':missing,'wrong_supply_reachable':ambiguous,'supply_bpin_component_counts':{k:len(v) for k,v in seeds.items()},'geometry_contact_PASS':not(grid_bad or via_bad or shorts or missing or ambiguous)}
(P/'metal_proof.json').write_text(json.dumps(result,indent=2)+'\n')
assert result['geometry_contact_PASS'], 'NATIVE_PG_CONTACT_FAIL'
print('NATIVE_PG_CONTACT_PASS',n,len(j['pins']))
