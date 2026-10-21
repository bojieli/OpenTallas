import re,json,hashlib
from pathlib import Path
r=Path('/srv/opentallas-scratch/claude/codex-q-s8-native-1021-c001/w12c/src')
spec=json.loads((r/'tools/ref_tile/specs_qw2_slice2_native/qfd_dv_slice2_w12c.json').read_text())
defs={};missing=[];files=[]
for p in spec['sources']:
 f=r/p
 if not f.exists(): missing.append(p);continue
 s=f.read_text()
 if p=='rtl/qwen_dv/qfd_dv_station_math_g.sv':
  s=s.replace('qfd_bmath_','qfd_s8legacy_bmath_');p='rtl/qwen_dv/s5/s8/qfd_dv_s8_legacy_math_g.sv'
 active=[];stack=[];enabled=True
 for line in s.splitlines():
  m=re.match(r'\s*`(ifdef|ifndef|else|endif)\b\s*(\w*)',line)
  if m:
   op,n=m.groups()
   if op in ('ifdef','ifndef'):
    cond=n in set(spec['defines']+['SYNTHESIS']);cond=cond if op=='ifdef' else not cond;stack.append((enabled,cond));enabled=enabled and cond
   elif op=='else': enabled=stack[-1][0] and not stack[-1][1]
   else: enabled=stack.pop()[0]
   continue
  if enabled:active.append(line)
 s='\n'.join(active)
 s=re.sub(r'/\*.*?\*/','',s,flags=re.S);s=re.sub(r'//[^\n]*','',s)
 for n in re.findall(r'\bmodule\s+([A-Za-z_$][\w$]*)',s):defs.setdefault(n,[]).append(p)
 files.append(p)
print(json.dumps({'scope':'source packaging inventory only; namespace substitution in memory; no native verdict','sources':files,'missing_files':missing,'module_definitions':len(defs),'duplicates':{k:v for k,v in defs.items() if len(v)>1}},indent=2))
