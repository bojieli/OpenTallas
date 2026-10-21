#!/usr/bin/env python3
"""Read-only attribution of an immutable mapped census; no admission or waiver."""
import sys,json,re,collections,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[3]))
import textbook_lint as T
src,out=map(Path,sys.argv[1:3]);raw=src.read_bytes();g,top=T.flatten(T.parse_verilog(raw.decode()),'dsdv_svc_att');print('PARSED',len(g.cells),len(g.net_name),flush=True)
# Only for attribution, fold actual unary BUF/INV paths regardless of polarity.
for typ,name,pins in g.cells:
 if re.match(r'^(BUF|INV)',typ)and 'Y'in pins and len(pins['Y'])==1:
  ip=[b for p,b in pins.items()if p!='Y']
  if len(ip)==1 and len(ip[0])==1:g.union(pins['Y'][0],ip[0][0])
names=collections.defaultdict(list)
for i,n in enumerate(g.net_name):
 if 'u_core'in n:names[g.find(i)].append(n)
root=g.find(g.net_id['rst_n']);counts=collections.Counter();examples=collections.defaultdict(list);unknown=[];reset_total=0;heads=collections.Counter()
for typ,nm,pins in g.cells:
 if re.match(r'^(BUF|INV)',typ):continue
 contacts=[p for p,b in pins.items()for bit in b if g.find(bit)==root]
 if not contacts:continue
 for p in contacts:
  if p in ['CLK','CK']:continue
  reset_total+=1;qs=[x for p,b in pins.items()if p in ['Q','QN']for x in b];aliases=[n for q in qs for n in names.get(g.find(q),[])]
  if aliases:
   n=max(aliases,key=lambda s:(s.count('.'),len(s)));field=re.sub(r'\[\d+\]','',n);counts[field]+=1;heads['.'.join(field.split('.')[:3])]+=1
   if len(examples[field])<2:examples[field].append({'cell':nm,'master':typ,'pin':p,'alias':n})
  else:
   field='UNATTRIBUTED:'+typ;counts[field]+=1
   if len(unknown)<20:unknown.append({'cell':nm,'master':typ,'pin':p,'outputs':qs})
r={'scope':'Immutable prior NORST map attribution only; not native qualification or permission to remove resets.','netlist_sha256':hashlib.sha256(raw).hexdigest(),'mapped_top':top,'cells':len(g.cells),'reset_contacts':reset_total,'expected_prior_census_reset_loads':8173,'head_counts':heads.most_common(),'field_counts':counts.most_common(),'examples':dict(examples),'unattributed_examples':unknown};out.write_text(json.dumps(r,indent=2)+'\n');print('RESET_ATTRIBUTION',reset_total,counts.most_common(18),flush=True)
