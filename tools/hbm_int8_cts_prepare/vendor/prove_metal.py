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
# A native DEF serialization permits PG ITerm binding lines only to differ.
a=(P/'before.def').read_text();b=(P/'after.def').read_text()
def sections(t):
 names=['COMPONENTS','PINS','SPECIALNETS','NETS','VIAS','REGIONS','BLOCKAGES','FILLS','NONDEFAULTRULES']
 return {name:(m.group(0) if (m:=re.search(r'^'+name+r'\b.*?^END '+name+r'\s*$',t,re.M|re.S)) else '') for name in names}
aa,bb=sections(a),sections(b); deltas={k:aa[k]!=bb[k] for k in aa}
# SPECIALNETS may add exactly 644 tuples; strip tuples and compare entire residual geometry.
def sp(t):return re.sub(r'\(\s+\S+\s+(?:VDD|VSS)\s+\)','',t)
normalized_special_equal=''.join(sp(aa['SPECIALNETS']).split())==''.join(sp(bb['SPECIALNETS']).split())
def signal_nets(text):
 parts=re.split(r'(?m)^\s+-\s+',text)[1:]
 return {z.split(None,1)[0]: z for z in parts if z.split(None,1)[0] not in ('VDD','VSS')}
signal_geometry_equal=signal_nets(aa['NETS'])==signal_nets(bb['NETS'])
assert signal_geometry_equal and normalized_special_equal
result={'signal_net_records_identical':signal_geometry_equal,'schema':'opentallas.pg_conductor_clone.v1','shapes':n,'via_instances':len(j['vias']),'cuts_checked':cuts,'grid_dbu':j['grid'],'grid_offenders':grid_bad,'via_enclosure_contact_failures':via_bad,'vdd_vss_same_layer_shorts':shorts,'pg_terminal_count':len(j['pins']),'pg_terminals_not_entirely_connected_to_matching_supply_bpins':missing,'wrong_supply_reachable':ambiguous,'supply_bpin_component_counts':{k:len(v) for k,v in seeds.items()},'def_section_changes':deltas,'specialnet_geometry_unchanged':normalized_special_equal,'geometry_contact_PASS':not(grid_bad or via_bad or shorts or missing or ambiguous),'source_def_sha256':hashlib.sha256(a.encode()).hexdigest(),'clone_def_sha256':hashlib.sha256(b.encode()).hexdigest()}
(P/'metal_proof.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:(len(v) if isinstance(v,list) else v) for k,v in result.items()}))
