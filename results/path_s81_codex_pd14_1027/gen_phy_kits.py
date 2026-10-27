#!/usr/bin/env python3
import hashlib,json,shutil,subprocess,sys
from pathlib import Path
W,O=map(Path,sys.argv[1:]);D=json.load(open(O/'die_plan_phy_contents.json'));types=[r['type'] for r in json.load(open(O/'phy_contents_report.json'))['rows']]
args=[];receipts=[]
# A staged plan keeps its original relative pin-table context even when only PHY types are emitted.
# The die/reset generator walks all types before slicing the requested kits.
base=Path('/srv/opentallas-scratch2/claude/path-s81-pd7-1026/d/src')
for f in {c['pins_file'] for t in D['partition_types'].values() for c in t.get('hard_cores',[]) if c.get('pins_file')}:
 src=base/f
 if not src.is_file():src=W/'physical/die_plan/s81'/f
 if not src.is_file():raise FileNotFoundError(f'original staged-plan pin context missing {f}')
 dst=O/f;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
B=Path('/srv/opentallas-scratch2/claude/s81-unblock-1027/b3/out/kit_rtl')
for tn in types:
 src=B/tn/'kit_rtl.f'
 if not src.is_file():
  k=O/'missing_kit_rtl'/tn
  cmd=[sys.executable,'-I',str(W/'tools/die_plan/bind.py'),'kit-rtl',str(O/'die_plan_phy_contents.json'),'--out',str(B.parent),'--type',tn,'--kit',str(k),'--asbuilt','physical/die_plan/s81/bind/asbuilt_b178_coll_pd7d.json']
  if not (k/'kit_rtl.f').is_file():
   with (O/('kit_'+tn+'.log')).open('w') as log:subprocess.run(cmd,cwd=W,stdout=log,stderr=subprocess.STDOUT,check=True)
  src=k/'kit_rtl.f'
 t=O/'phy_rtl'/tn;t.mkdir(parents=True,exist_ok=True);fs=[]
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
