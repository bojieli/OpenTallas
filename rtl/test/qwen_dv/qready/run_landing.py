#!/usr/bin/env python3
"""Private source-snapshot runner. JSON sources are pinned to9f159ab98; writes only its supplied workdir."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--layer',type=int,choices=(0,1),default=0);ap.add_argument('--ideal-control',action='store_true');ap.add_argument('--late',action='store_true');ap.add_argument('--reuse',action='store_true');a=ap.parse_args()
root=Path.cwd();x=json.loads((root/f'trace/L{a.layer}_q_trace.json').read_text())
q=[0]*5000
for r in x['words']:q[r['edge_w5']+64]=int(r['word'],16)
(root/'qdd.memh').write_text(''.join(f'{w:0137x}\n' for w in q))
(root/'qgold.memh').write_text(''.join(r['bits']+'\n' for r in x['seats']))
receipt=json.loads((root/'sources.json').read_text())
for p,want in receipt['sha256'].items():
 if hashlib.sha256((root/p).read_bytes()).hexdigest()!=want:raise ValueError('source snapshot changed: '+p)
src=list(receipt['paths'])
suffix=('control' if a.ideal_control else 'production')+('_late' if a.late else '')
obj=root/('obj_landing_'+suffix)
log=root/f'landing_{suffix}_L{a.layer}.log'
src+=['rtl/test/qwen_dv/qready/tb_qready_landing.sv']
cpp=root/'rtl/test/qwen_dv/qready/qready_main.cpp'
cmd=['verilator','--cc','--exe','--build','-j','4','-O2','-Wno-fatal','-Wno-lint','-Wno-style',
     '--top-module','tb_qready_landing','-GSAFE=2',f'-GIDEAL_CONTROL={int(a.ideal_control)}',f'-GLATE_PREFETCH={int(a.late)}','-Mdir',str(obj)]+src+[str(cpp)]
if not a.reuse:
 with (root/f'landing_{suffix}_build.log').open('w') as f:
  rc=subprocess.call(cmd,stdout=f,stderr=subprocess.STDOUT)
 if rc:sys.exit(rc)
with log.open('w') as f:
 rc=subprocess.call([str(obj/'Vtb_qready_landing'),'+QDD='+str(root/'qdd.memh'),'+QGOLD='+str(root/'qgold.memh')],stdout=f,stderr=subprocess.STDOUT)
print(log.read_text());sys.exit(rc)
