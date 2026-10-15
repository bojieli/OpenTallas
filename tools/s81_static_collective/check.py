#!/usr/bin/env python3
"""Small four-rank actual RTL mechanism proof, never native token qualification."""
import argparse, hashlib, json, subprocess, tempfile
from pathlib import Path
from calendar import calendar, model, vm_events
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
repo=Path(__file__).resolve().parents[2];a.out.mkdir(parents=True,exist_ok=True)
sources=sorted((repo/'rtl/dsrom_sys/s81_static_collective').glob('*.sv'))
records=[]
with tempfile.TemporaryDirectory(prefix='s81-static-') as td:
 exe=Path(td)/'sim'
 subprocess.run(['iverilog','-g2012','-s','tb_s81_static_tp4','-o',str(exe),*map(str,sources)],check=True)
 for layer,kind in [(0,'a'),(2,'a'),(8,'a'),(14,'a'),(20,'a'),(0,'router')]:
  slots=calendar(layer,0,kind=kind);plan=a.out/f'{kind}_L{layer}.mem'
  plan.write_text(''.join(f'{(s.issue<<96)|(s.commit<<64)|(sum(r<<(15*k) for k,r in enumerate(s.rows))<<4)|(s.last<<3):032x}\n' for s in slots))
  for mut in range(7) if layer==2 else [0]:
   cp=subprocess.run(['vvp',str(exe),f'+N={len(slots)}',f'+MUT={mut}',f'+PLAN={plan.resolve()}'],text=True,capture_output=True)
   log=a.out/f'{kind}_L{layer}_m{mut}.log';log.write_text(cp.stdout+cp.stderr)
   if cp.returncode or 'PASS component-only' not in cp.stdout:raise RuntimeError(str(log))
   records.append(dict(layer=layer,kind=kind,mutant=mut,verdict='PASS' if mut==0 else 'MUTANT_DETECTED',
     records_per_rank=len(slots),fp32_per_destination=len(slots)*64,
     first_commit=slots[0].commit,last_commit=slots[-1].commit,log=log.name))
# The reservations below check API validation only; no VM capacity claim.
slots=calendar(2,0)
events=vm_events(slots,identity=0x78,reservations={(s.seq,r):(0,0) for s in slots for r in range(4)},drain_delays={(s.seq,r):0 for s in slots for r in range(4)})
assert len(events)==176 and events[-1]['observation_edge']==187
try: vm_events(slots,identity=0x78,reservations={},drain_delays={})
except ValueError: pass
else: raise AssertionError('missing reservations accepted')
with tempfile.TemporaryDirectory(prefix='s81-source-') as td:
 exe=Path(td)/'source_sim'
 subprocess.run(['iverilog','-g2012','-s','tb_s81_static_tp4_vm_read_source','-o',str(exe),*map(str,sources)],check=True)
 cp=subprocess.run(['vvp',str(exe)],text=True,capture_output=True)
 (a.out/'vm_read_source_interface.log').write_text(cp.stdout+cp.stderr)
 if cp.returncode or 'PASS interface-only' not in cp.stdout:raise RuntimeError('source API proof')
report=dict(model=model(),source_sha256={str(s.relative_to(repo)):hashlib.sha256(s.read_bytes()).hexdigest() for s in sources},
            calendar_sha256=hashlib.sha256((Path(__file__).parent/'calendar.py').read_bytes()).hexdigest(),
            mutants=['missing source','late PHY beat','reordered sequence','wrong rankmask','corrupt PHY payload','VM out-of-range row'],cases=records)
(a.out/'receipt.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(cases=len(records),verdict='PASS_COMPONENT_ONLY',native_token=False)))
