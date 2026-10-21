import re,json,hashlib
from pathlib import Path
p=Path('/srv/opentallas-scratch/claude/ref_gate/codex_health_parameters_1020/actual_d5p/diagnostic_run/port_bind_v2/die_bound.v');raw=p.read_bytes();text=raw.decode();rows=[]
for module,name,body in re.findall(r'^\s*(\w+)\s+(slg_\w+)\s*\((.*?)\);',text,re.M|re.S):
 q={'module':module,'instance':name,'ports':{}}
 for f in ['cfg_stack','cfg_group']:
  m=re.search(r'\.slg__'+f+r'\(\s*([^)]*?)\s*\)',body);assert m,(name,f)
  pins=m.group(1);bits=re.findall(r"1'b([01])",pins);assert bits,(name,f,pins);q['ports'][f]={'actual_expression':pins,'value':int(''.join(bits),2)}
 rows.append(q)
assert len(rows)==32,len(rows)
print(json.dumps(dict(scope='READ-ONLY diagnostic actual d5p bound graph; strict diagnostic source index FAIL, not production qualification',path=str(p),sha256=hashlib.sha256(raw).hexdigest(),groups=rows),indent=1))
