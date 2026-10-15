#!/usr/bin/env python3
"""Exercise each native resident-ROM fn row with released full-size H vectors.
Run in admitted environment; arithmetic and physical via mapping are real RTL.
The binary must be source-pinned tb_s81_hcx_projection_leaf (W32,264 cycles).
This validates projection components, not native full-token transport.
"""
import argparse,importlib.util,json,subprocess,hashlib
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--vectors',type=Path,required=True);p.add_argument('--binary',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--cases',nargs='*');a=p.parse_args()
spec=importlib.util.spec_from_file_location('vectors',Path(__file__).with_name('hcx_projection_vectors.py'));v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
cases=sorted(list((a.vectors/'vec').glob('L*'))+list((a.vectors/'vecm').glob('M*')))
if a.cases:cases=[c for c in cases if c.name in a.cases]
a.out.mkdir(parents=True,exist_ok=True);rows=[]
for c in cases:
 for row in range(24):
  dest=a.out/c.name/f'r{row:02d}';v.build(c,dest,row)
  r=subprocess.run([str(a.binary.resolve()),f'+DIR={dest.resolve()}',f'+OT_ROM_DIR={dest.resolve()}'],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
  (dest/'run.log').write_text(r.stdout)
  if r.returncode or 'HCX_PROJECTION PASS' not in r.stdout:raise RuntimeError(f'{c.name} row{row}: exit{r.returncode}, see {dest}/run.log')
  rows.append(dict(case=c.name,row=row,exact_fp32_outputs=2,native_serial_cycles=264))
  print(f'HCX_NATIVE_ROW {c.name} row{row} exact2 cycles264',flush=True)
  # Physical ROM images can be regenerated from source; preserve only receipts.
  for f in dest.glob('*.viamap.hex'):f.unlink()
  for f in dest.glob('x*.mem'):f.unlink()
(a.out/'summary.json').write_text(json.dumps(dict(scope='native projection components only',binary_sha256=hashlib.sha256(a.binary.read_bytes()).hexdigest(),cases=len(cases),rows=rows,exact_outputs=len(rows)*2),indent=2)+'\n')
print(f'HCX_NATIVE_SWEEP PASS cases{len(cases)} rows{len(rows)} exact_outputs{len(rows)*2}',flush=True)
