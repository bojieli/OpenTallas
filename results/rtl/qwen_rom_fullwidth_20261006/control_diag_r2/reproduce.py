from pathlib import Path
import json,re,subprocess,hashlib,os,time
b=Path('/srv/opentallas-scratch2/codex/item1-qwen-fullwidth-20261006/full-r1')
o=b.parent/'control-diag-r2'
o.mkdir(exist_ok=False)
import shutil
for header in (b/'host').glob('*.hpp'): shutil.copyfile(header,o/header.name)
for header in (b/'host').glob('*.h'): shutil.copyfile(header,o/header.name)
r=json.loads((b/'prepared.json').read_text())
h=(b/'die/Vdie___024root.h').read_text()
fields=[]
for name in re.findall(r'CData/\*[^*]+\*/\s+(\w+);',h):
 if 'stack__BRA__0__KET__' in name and any(s in name for s in ('u_state__DOT__primary','u_state__d','u_control__DOT__ca','u_control__DOT__ga','u_control__DOT__u_cs__DOT__primary','u_control__d_v')):fields.append(name)
assert len(fields)>=6,fields
s=(b/'host/fulltoken.cpp').read_text()
inject='if (tick<=16) { printf("CONTROL_DIAG tick=%ld cyc=%u",tick,cyc);\n'
for field in fields:inject+='printf(" '+field.split('stack__BRA__0__KET__')[-1]+'=%x",unsigned(die[0]->rootp->'+field+'));\n'
inject+='printf("\\n"); fflush(stdout); }\nif(tick>16) return 2;\n'
assert s.count('uint32_t cyc = die[0]->cyc;')==1
s=s.replace('uint32_t cyc = die[0]->cyc;','uint32_t cyc = die[0]->cyc;\n'+inject)
(o/'fulltoken.cpp').write_text(s)
link=[str(o/'fulltoken.cpp') if x==str(b/'host/fulltoken.cpp') else str(o/'fulltoken') if x==str(b/'fulltoken') else x for x in r['link']]
run=[str(o/'fulltoken') if x==str(b/'fulltoken') else str(o/'run') if x==str(b/'run') else x for x in r['runtime']]
(o/'prepared.json').write_text(json.dumps(dict(link=link,runtime=run,fields=fields,original_prepared_sha256=hashlib.sha256((b/'prepared.json').read_bytes()).hexdigest(),scope='Diagnostic host-only relink; identical retained compiled RTL; stop by initial cycle16'),indent=2)+'\n')
for phase,cmd in [('link',link),('runtime',run)]:
 with (o/(phase+'.log')).open('x') as f:rc=subprocess.call(cmd,stdout=f,stderr=subprocess.STDOUT)
 (o/(phase+'.exit')).write_text(str(rc)+'\n')
 if rc:raise SystemExit(rc)
