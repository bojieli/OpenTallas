#!/usr/bin/env python3
"""Read-only native corner replay in own audit directory; fleet runner required."""
from pathlib import Path
import subprocess,hashlib,json,argparse
p=argparse.ArgumentParser();p.add_argument('--manifest');a=p.parse_args();out=[]
records=json.loads(Path(a.manifest).read_text())if a.manifest else [dict(half=h,run=f'/srv/opentallas-scratch/claude/ref_gate/qfd_c_land_{h}258_narrow-20261019-084057',kit=f'physical/ref_tile/qfd_c_land_{h}258_narrow/signoff.sdc')for h in 'wr']
for record in records:
 h=record['half'];r=Path(record['run']);kit=record['kit']
 work=r/'routes/gate/work/orfs'; base=next((work/'results/asap7').glob('*/base'))
 for c in ['TT','FF']:
  log=Path(f'corner_{h}_{c}.log')
  cmd=['docker','run','--rm','-e',f'CB16_CORNER={c}','-e',f'CB16_SIGNOFF=/src/{kit}','-v',f'{r}/src:/src:ro','-v',f'{work}:/work:ro','-v',f'{Path.cwd()}:/audit','openroad/orfs:latest','/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad','-no_init','-exit','/audit/cb16_corner_replay.tcl']
  with log.open('w')as f: subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
  print(h,c,[l for l in log.read_text().splitlines()if l.startswith('CB16_CORNER')],flush=True)
  out.append(dict(half=h,corner=c,log=str(log),inputs={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in [base/'5_1_grt.odb',base/'5_1_grt.sdc',r/'src'/kit]}))
Path('corner_sources.json').write_text(json.dumps(out,indent=1)+'\n')
