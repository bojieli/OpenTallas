import ast
import runpy
from pathlib import Path
import unittest
from unittest.mock import patch

HERE=Path(__file__).parent
OLD=runpy.run_path(str(HERE/'ot-heavy-reconcile.original.py'),run_name='readonly_old')
NEW=runpy.run_path(str(HERE/'ot-heavy-reconcile.proposed.py'),run_name='readonly_new')

class Snapshot(unittest.TestCase):
 def test_admission_arithmetic_and_lock_code_unchanged(self):
  def functions(file):
   return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(file.read_text()).body if isinstance(n,ast.FunctionDef)}
  a=functions(HERE/'ot-heavy-reconcile.original.py');b=functions(HERE/'ot-heavy-reconcile.proposed.py')
  for name in ('gate','books','admissible','charged_growth','die_hold','prio_waiters','set_res','main'):
   self.assertEqual(a[name],b[name],name)

 def test_mixed_active_inactive_nested_rows_match_and_calls_drop(self):
  outputs=[]
  for module in (OLD,NEW):
   ns=module['read_units'].__globals__; ns['NOW']=1000
   calls=[]
   def sh(*args):
    calls.append(args)
    if '--property=Id' in args:
     return 'Id=oth-a.scope\nControlGroup=/direct\n\nId=oth-b.scope\nControlGroup=\n\nId=oth-c.scope\nControlGroup=/nested'
    return '/nested' if 'oth-c.scope' in args else ''
   def rd(path):
    if path.endswith('/res.oth-a'):return 'oth-a 32'
    if path.endswith('/res.oth-b'):return 'oth-b 16'
    if path.endswith('/res.oth-c'):return 'oth-c 48'
    if path.endswith('memory.current'):return str(2*1073741824)
    if path.endswith('memory.peak'):return str(3*1073741824)
    if path.endswith('memory.max'):return str(32*1073741824)
    return ''
   def glob(pattern):
    if pattern.endswith('/res.*'):return ['/fake/res.oth-a','/fake/res.oth-b','/fake/res.oth-c']
    return ['/sys/fs/cgroup/direct'] if 'oth-a.scope' in pattern else []
   ns['rd']=rd;ns['sh']=sh
   with patch('glob.glob',glob),patch('os.path.isdir',lambda p:p in ('/sys/fs/cgroup/direct','/sys/fs/cgroup/nested')),patch('os.path.getmtime',lambda p:990):
    rows=module['read_units']()
   outputs.append(rows)
   self.assertEqual(len(calls),2 if module is OLD else 1)
  self.assertEqual(outputs[0],outputs[1])
  self.assertEqual([r['active'] for r in outputs[1]],[True,False,True])

 def test_missing_or_malformed_snapshot_uses_per_unit_fallback(self):
  fn=NEW['fast_cg'];ns=fn.__globals__
  old=ns['scope_cg'];ns['scope_cg']=lambda unit:'fallback-'+unit
  try:
   with patch('glob.glob',lambda p:[]):
    self.assertEqual(fn('oth-x',None),'fallback-oth-x')
    self.assertEqual(fn('oth-x',{}),'fallback-oth-x')
    self.assertEqual(fn('oth-x',{'oth-other':None}),'fallback-oth-x')
    self.assertIsNone(fn('oth-x',{'oth-x':None}))
  finally:ns['scope_cg']=old

 def test_empty_failed_or_unparseable_bus_preserves_fallback(self):
  fn=NEW['scope_cgroup_snapshot'];ns=fn.__globals__;old=ns['sh']
  try:
   for raw in ('','garbled','ControlGroup=/orphan','Id=other.scope\nControlGroup=/wrong'):
    ns['sh']=lambda *args:raw
    self.assertIsNone(fn(['oth-x']))
   ns['sh']=lambda *args:'Id=oth-x.scope\nControlGroup='
   self.assertEqual(fn(['oth-x']),{'oth-x':None})
  finally:ns['sh']=old

if __name__=='__main__':unittest.main(verbosity=2)
