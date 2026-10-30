#!/usr/bin/env python3
"""Exact equivalent-proof reuse, full native LEC fallback, fail closed on unproved."""
import sys,json,subprocess
from pathlib import Path
k=Path(sys.argv[1]);out=k/'lec'
r=subprocess.run([sys.executable,'-I',str(k/'check_logic_reuse.py'),str(k)],capture_output=True,text=True)
(k/'lec_reuse.log').write_text(r.stdout+r.stderr)
if r.returncode==0:
 print(r.stdout,end='');sys.exit(0)
print('LEC reuse identity differs; executing full native proof')
r=subprocess.run([sys.executable,'-I',str(k/'lec.py')]+sys.argv[1:])
try:equivalent=json.load(open(out/'lec.json'))['verdict']=='EQUIVALENT'
except (OSError,KeyError,ValueError):equivalent=False
sys.exit(0 if equivalent and r.returncode==0 else 1)
