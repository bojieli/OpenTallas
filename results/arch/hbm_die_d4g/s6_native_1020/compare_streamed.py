import json,sys,copy,hashlib
from pathlib import Path
rows=json.loads(Path(sys.argv[1]).read_text());out=Path(sys.argv[2]);records=[]
for row in rows:
 cell=row['cell'];old=json.loads(Path(row['canonical_cli_report']).read_text());new=json.loads((out/cell/'native.json').read_text())
 a,b=copy.deepcopy(old),copy.deepcopy(new)
 a['netlist'].pop('path',None);b['netlist'].pop('path',None)
 assert a==b,(cell,[k for k in set(a)|set(b) if a.get(k)!=b.get(k)])
 records.append({'cell':cell,'full_report_equal':True,'normalized_only':['netlist.path'],'status':old['status'],'max_dynamic_loads':old.get('max_dynamic_loads'),'mapped_sha256':old['netlist']['sha256'],'liberty':[{'path':l['path'],'sha256':l['sha256']} for l in old['liberty']]})
assert {r['status'] for r in records}=={'PASS','FAIL'}
assert len({tuple((l['path'],l['sha256']) for l in r['liberty']) for r in records})>=2
(out/'CLI_FULL_EQUALITY.json').write_text(json.dumps(records,indent=2)+'\n');print('CANONICAL_FULL_REPORT_EQUAL',len(records),'PASS+FAIL+macro/distinctLibset')
