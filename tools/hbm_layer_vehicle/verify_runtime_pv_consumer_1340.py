#!/usr/bin/env python3
"""Pure existing-calendar compatibility and no-P-input check; no RTL execution."""
import sys, subprocess, types, json
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'tools/hbm_sm_attention'));sys.path.insert(0,str(Path.cwd()/'tools'))
import sm_elem_bench as E
old=types.ModuleType('old_sm_elem');old.__file__=E.__file__
exec(compile(subprocess.check_output(['git','show','a356b30971e2a267ff01d4e797d5ff8cc1e86c89:tools/hbm_sm_attention/sm_elem_bench.py'],text=True),E.__file__,'exec'),old.__dict__)
rec=E.B.make_record(128,0,1015);op=('pv_sm0','pv',0,list(range(8)),1)
a,ea=old.compile_op(rec,op,E.DEFAULT_LAT,True);b,eb=E.compile_op(rec,op,E.DEFAULT_LAT,True)
assert vars(a)==vars(b) and ea==eb
class NoProbability(dict):
 def __getitem__(self,k):
  if k=='p':raise AssertionError('runtime consumer read fixture probabilities')
  return super().__getitem__(k)
mp={r:120+r for r in range(8)}
c,ex=E.compile_op(NoProbability(rec),op,E.DEFAULT_LAT,True,runtime_probability_rows=mp)
assert not c.xw
reads=[(i,x['paddr']) for i,x in enumerate(c.cyc) if x.get('pread')]
assert {x for i,x in reads}==set(mp.values())
assert len(reads)==64
for bad in [{r:0 for r in range(8)},{r:128+r for r in range(8)},{0:0}]:
 try:E.compile_op(NoProbability(rec),op,E.DEFAULT_LAT,True,runtime_probability_rows=bad)
 except ValueError:pass
 else:raise AssertionError('invalid mapping accepted')
print(json.dumps(dict(status='PASS_PURE_COMPILER_ONLY',hardware_executed=False,legacy_calendar_identical=True,runtime_fixture_probability_accesses=0,runtime_probability_preloads=0,pread_commands=len(reads),explicit_page_addresses=sorted(set(x for _,x in reads)),runtime_consumer_end=ex['end'],join_qualified=False)))
