"""Re-evaluate saved actual c6231103d production g-port logs; no RTL rebuild."""
import sys,hashlib,runpy,json
from pathlib import Path
ns=runpy.run_path(str(Path(__file__).with_name('run_production.py')))
B=ns['B']; B.MU_NU=4;B.FACE=1;B.install()
B.VFLAGS[:]=['+define+OT_QFD_DV_SAFE_STORAGE','-GSU_LT=1','-GHD_W130=1']
def parse(p):
 out={}
 for line in p.read_text().splitlines():
  if line.strip():
   c,nm,h=line.split();out.setdefault(nm,[]).append((int(c)-B.RESET_WARM,int(h.replace('x','0').replace('X','0').replace('z','0'),16)))
 out['S0SC']=[(c,B.conv48(w)) for c,w in out.get('S0SU',[])]
 out['S1SC']=[(c,B.conv48(w)) for c,w in out.get('S1SD',[])]
 out['S1DD']=out.get('S0DD',[])
 return out
for fn in sys.argv[1:]:
 p=Path(fn);saved=parse(p)
 B.B.run_sim=lambda *a,**k:saved
 ok,n,errs=B.BENCHES['g'](Path('/tmp/head_saved_review'),0)
 print('SAVED_ACTUAL_MUTANT',p.name,'SHA256',hashlib.sha256(p.read_bytes()).hexdigest())
 print('bench2(g) verdict', 'FAIL' if ok!=n or errs else 'PASS',str(ok)+'/'+str(n))
 for e in errs: print(e)
 if ok==n and not errs:raise SystemExit('MUTANT_UNEXPECTED_PASS')
