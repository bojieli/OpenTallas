#!/usr/bin/env python3
import hashlib,json,shutil,subprocess,sys
from pathlib import Path
W,O=map(Path,sys.argv[1:]);D=json.load(open(O/'die_plan_phy_contents.json'));types=[r['type'] for r in json.load(open(O/'phy_contents_report.json'))['rows']]
args=[];receipts=[]
B=Path('/srv/opentallas-scratch2/claude/s81-unblock-1027/b3/out/kit_rtl')
for tn in types:
 src=B/tn/'kit_rtl.f';t=O/'phy_rtl'/tn;t.mkdir(parents=True,exist_ok=True);fs=[]
 for f in src.read_text().splitlines():
  if not f.strip():continue
  p=Path(f);dest=t/p.name
  if dest.exists() and dest.read_bytes()!=p.read_bytes():raise ValueError(f'basename collision{dest}')
  shutil.copy2(p,dest);fs.append(str(dest));receipts.append(dict(type=tn,source=str(p),copy=str(dest),sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
 ff=t/'kit_rtl.f';ff.write_text('\n'.join(fs)+'\n');args+=['--kit-rtl',tn+'='+str(ff)]
(O/'phy_rtl_receipts.json').write_text(json.dumps(receipts,indent=1)+'\n')
(O/'phy_gen').mkdir(exist_ok=True)
with (O/'phy_gen.log').open('w') as log:
 cmd=[sys.executable,'-I',str(W/'tools/die_plan/gen.py'),'phys',str(O/'die_plan_phy_contents.json'),'--out',str(O/'phy_gen'),'--types',','.join(types),'--rtl-root',str(W),'--hold-ff-margin','5','--max-wire-um','100']+args
 r=subprocess.run(cmd,cwd=W,stdout=log,stderr=subprocess.STDOUT)
(O/'phy_gen_result.json').write_text(json.dumps(dict(source='codex/s81-pd14-0818',types=types,rc=r.returncode,log=str(O/'phy_gen.log')),indent=1)+'\n');sys.exit(r.returncode)
