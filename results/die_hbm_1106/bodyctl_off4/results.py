from pathlib import Path
import re,json,gzip,glob,collections
r=Path('/work');areas={}
for p in glob.glob('/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT_TT*.lib*'):
 if 'FAKE' in p:continue
 s=gzip.open(p,'rt').read() if p.endswith('.gz') else Path(p).read_text()
 for m in re.finditer(r'cell\s*\(\s*([^\s)]+)\s*\)\s*\{',s):
  a=re.search(r'\barea\s*:\s*([0-9.eE+-]+)',s[m.end():]);assert a;areas[m[1]]=float(a[1])
res={}
for p in r.glob('**/*.sta.log'):
 w=re.findall(r'worst slack max ([0-9.-]+)',p.read_text())
 if not w:continue
 d=json.loads(p.with_name(p.name.replace('.sta.log','.mapped.json')).read_text());mod=d['modules'][p.name.split('.')[0]];cells=mod.get('cells',{});k=collections.Counter(c['type'] for c in cells.values())
 res[str(p.relative_to(r))]={'arrival_ps':round(833-float(w[-1]),2),'cells':len(cells),'liberty_area':round(sum(areas[n]*cnt for n,cnt in k.items()),6)}
(r/'mapping_results.json').write_text(json.dumps(res,indent=2)+'\n');print(json.dumps(res,indent=2))
(r/'cell_areas.json').write_text(json.dumps(areas,indent=2)+'\n')
