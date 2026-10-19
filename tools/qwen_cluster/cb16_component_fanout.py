#!/usr/bin/env python3
"""Native flattened mapped FF/control audit; use fleet runner in own audit dir."""
import argparse,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('manifest');a=p.parse_args()
for r in json.loads(Path(a.manifest).read_text()):
 label=r['half'];run=Path(r['run']);net=next((run/'routes/gate/work/orfs/results/asap7').glob('*/base/1_2_yosys.v'))
 if 'top'in r:top=r['top'];ff=r['flops']
 elif label.startswith('reset'):top='qfd_c_reset_epoch';ff=2 if label=='reset2'else 9
 else:ff=int(label[3:]);top=f'qfd_c_stn{ff}'
 subprocess.run(['docker','run','--rm','-v',f'{net.parent}:/in:ro','-v',f'{Path.cwd()}:/out','openroad/orfs:latest','python3','/out/flatten_for_audit.py',label,top],check=True)
 subprocess.run(['python3','qc_flat_fanout.py',f'flat_{label}.json','--top',top,'--flops',str(ff),'--out',f'flat_fanout_{label}.json'],check=True)
