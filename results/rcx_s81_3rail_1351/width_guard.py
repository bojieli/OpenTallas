import json,re,sys
from pathlib import Path
rules=Path(sys.argv[1]); geom=Path(sys.argv[2]); required={round(s['width_um'],6) for s in json.loads(geom.read_text())['segments']}; layers={s['layer'] for s in json.loads(geom.read_text())['segments']}
text=rules.read_text(); missing=[];coverage=[]
for m in re.finditer(r'^Metal ([89]) ([A-Z]+)\nWIDTH Table ([0-9]+) entries:([^\n]*)',text,re.M):
 layer='M'+m[1]
 if layer not in layers or int(m[3])==0:continue
 have={round(float(x),6) for x in m[4].split()};bad=sorted(required-have)
 coverage.append({'layer':layer,'kind':m[2],'widths_um':sorted(have)})
 if bad:missing.append({'layer':layer,'kind':m[2],'unsupported_widths_um':bad})
for layer in layers:
 if not any(x['layer']==layer for x in coverage):missing.append({'layer':layer,'missing_all_tables':True})
print(json.dumps({'verdict':'FAIL' if missing else 'PASS','required_widths_um':sorted(required),'missing':missing,'coverage':coverage},indent=1))
raise SystemExit(bool(missing))
