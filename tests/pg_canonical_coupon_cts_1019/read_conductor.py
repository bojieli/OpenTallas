"""Finite native PG shape graph, including via enclosures/cuts and actual BPin roots."""
from pathlib import Path
import json,sys,collections
p=Path(sys.argv[1]);j=json.loads(p.read_text());s=j['pg_shapes'];parent=list(range(len(s)))
def root(k):
 while parent[k]!=k:parent[k]=parent[parent[k]];k=parent[k]
 return k
def union(a,b):parent[root(a)]=root(b)
def touches(a,b):return max(a[0],b[0])<=min(a[2],b[2]) and max(a[1],b[1])<=min(a[3],b[3])
by_layer=collections.defaultdict(list);by_via={}
for k,a in enumerate(s):
 by_layer[(a['net'],a['layer'])].append(k)
 if a['via'] is not None:
  key=(a['net'],a['via'])
  if key in by_via:union(k,by_via[key])
  else:by_via[key]=k
for inds in by_layer.values():
 active=[]
 for k in sorted(inds,key=lambda k:s[k]['box'][0]):
  a=s[k]['box'];active=[t for t in active if s[t]['box'][2]>=a[0]]
  for t in active:
   if touches(a,s[t]['box']):union(k,t)
  active.append(k)
roots=set();unmatched_roots=[]
for pin in j['pins']:
 if pin['role'] not in ('POWER','GROUND'):continue
 hits=[k for k in by_layer[(pin['net'],pin['layer'])] if touches(pin['box'],s[k]['box'])]
 if not hits:unmatched_roots.append(pin)
 roots.update(root(k) for k in hits)
components=collections.defaultdict(list)
for k,a in enumerate(s):components[(a['net'],root(k))].append(k)
unrooted=[{'net':net,'shape_count':len(inds)} for (net,r),inds in components.items() if r not in roots]
contacts=[];missing=[]
for t in j['terms']:
 if t['role'] not in ('POWER','GROUND'):continue
 # This exact coupon has one native CORE voltage domain VDD/VSS; verify the
 # independent native-PG snapshot's rules separately. No terminal is bound here.
 expected='VDD' if t['role']=='POWER' else 'VSS'
 for g in t['geometry']:
  hits=[k for k in by_layer[(expected,g['layer'])] if touches(g['box'],s[k]['box']) and root(k) in roots]
  r={'instance':t['instance'],'pin':t['pin'],'bound_net':t['net'],'expected_coupon_core_net':expected,'shape':g,'rooted_hits':len(hits)}
  (contacts if hits else missing).append(r)
result={'source_odb_sha256':j['sha256'],'shape_count':len(s),'native_vias':j['pg_via_count'],'conductor_components':[{'net':net,'shape_count':len(inds),'rooted':r in roots} for (net,r),inds in components.items()],'unrooted':unrooted,'unmatched_pg_bpins':unmatched_roots,'term_rectangle_contacts_to_rooted_native_core_pg':len(contacts),'missing_term_rectangle_contacts':missing,'native_metadata_unbound_terms':len(j['pg_unbound']),'cross_net_short_shape_count':len(j['pg_cross_net_short_shapes']),'wrong_bound_pin_contacts':len(j['pg_wrong_pin_contacts']),'scope':'Geometric native PG union/contact proof for exact single CORE domain; independent of metadata binding, native DRC, signal-route shorts, IR/EM, and extracted timing.'}
p.with_name('conductor.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
