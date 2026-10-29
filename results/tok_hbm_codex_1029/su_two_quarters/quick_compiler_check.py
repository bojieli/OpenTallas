#!/usr/bin/env python3
"""Small combined gate: normative Engram arithmetic + two legacy4Q byte checks."""
import argparse,contextlib,io,subprocess,sys,tempfile,unittest
from pathlib import Path
from types import ModuleType,SimpleNamespace
ROOT=Path(__file__).resolve().parents[3]
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--baseline',default='a1d3c708f');a=p.parse_args()
source=ROOT/'tools/hbm_static/toksim_su/suvop/prod_compile.py'
sys.path.insert(0,str(source.parent));import prod_compile as candidate
old=ModuleType('legacy_source');old.__file__=str(source);sys.modules[old.__name__]=old
exec(compile(subprocess.check_output(['git','show',a.baseline+':'+str(source.relative_to(ROOT))],cwd=ROOT).decode(),str(source),'exec'),old.__dict__)
with tempfile.TemporaryDirectory(prefix='su_legacy4q_') as scratch:
 for record in ('ds_moe_sum2','ds_route_total'):
  for mod,label in ((old,'old'),(candidate,'new')):
   mod.MLAT,mod.ALAT,mod.WCOPY=4,3,0;mod.LIN=mod.SLB.lin(4,3,1)
   opts=SimpleNamespace(out=str(Path(scratch)/record/label),rec=record,quarters=4,pin_reg=None,full_side=True,
    rr=25,wr=22,fill_slack=1,drain_slack=2,side_ii=0,rfd_slack=1,pretree=True,qpr=1)
   with contextlib.redirect_stdout(io.StringIO()):mod.compile_rec(opts)
  for file in ('prog.mem','expw.mem','exps.mem','explw.mem','programme.json','arith/seed.mem','tree.mem'):
   x=Path(scratch)/record/'old'/file;y=Path(scratch)/record/'new'/file
   if x.exists() or y.exists():assert x.read_bytes()==y.read_bytes(),(record,file,'legacy4Q changed')
  print('LEGACY4Q_BYTE_IDENTICAL',record)
r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.discover(str(source.parent),pattern='test_actual_engram_gate.py'))
if not r.wasSuccessful():raise SystemExit(1)
print('QUICK_COMPILER_PASS')
