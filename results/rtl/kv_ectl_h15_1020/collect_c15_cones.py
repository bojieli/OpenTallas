"""Read-only complete endpoint diagnostic; no admission/threshold change."""
from pathlib import Path
import hashlib,inspect,json,sys
sys.path.insert(0,'/src/tools/ref_tile');sys.path.insert(0,'/src/tools')
import native_census as N
p=Path('/work/native_census.json');r=json.loads(p.read_text());n=Path(r['netlist']['path']);raw=n.read_bytes();assert hashlib.sha256(raw).hexdigest()==r['netlist']['sha256']
roles,libs=N.liberty_roles([x['path'] for x in r['liberty']]);assert libs==r['liberty']
mods=N.TL.parse_verilog(raw.decode());mods={k:v for k,v in mods.items() if k==r['top'] or k not in roles};g,_=N.TL.flatten(mods,r['top'])
source=inspect.getsource(N.census);assert source.count('[:40]')==1
ns=dict(N.__dict__);exec(source.replace('[:40]',''),ns);full=ns['census'](g,roles)
fields=lambda x:{k:v for k,v in x.items() if k!='endpoints'}
assert [fields(x) for x in full['violations']]==[fields(x) for x in r['violations']]
aliases={}
for name,i in g.net_id.items():aliases.setdefault(g.find(i),[]).append(name)
byname={g.net_name[i]:i for i in aliases}
rows=[]
for v in full['violations']:
 ep=[]
 for ci,pin,bit in v['endpoints']:
  if ci=='port':ep.append(dict(port=pin,bit=bit));continue
  master,name,_=g.cells[ci];ep.append(dict(instance=name,master=master,pin=pin,bit=bit))
 assert len(ep)==v['loads']
 rows.append(dict(**fields(v),net_aliases=aliases.get(byname.get(v['net']),[]),complete_endpoints=ep))
out=dict(scope='READ_ONLY_FULL_NATIVE_FAIL_CONES_NO_ADMISSION',mapped=r['netlist'],liberty=libs,helper_sha256=hashlib.sha256(Path(N.__file__).read_bytes()).hexdigest(),source_edit='only diagnostic endpoint display truncation40 removed in memory; identical7violations/counts/roles asserted',violations=rows)
Path('/work/full_cones.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps([dict(driver=x['driver'],loads=x['loads'],aliases=x['net_aliases']) for x in rows]))
