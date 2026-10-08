import copy
import tempfile
import unittest
from pathlib import Path
from hbm_result_relay_hold_patch import FILES, endpoints, make_plan, parse_timing, prepare, sha, validate

class HoldPatch(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.root=Path(self.tmp.name);self.base=self.root/'base';self.base.mkdir()
  for name in FILES:(self.base/name).write_text('fixture '+name)
  row=dict(odb_sha256=sha(self.base/FILES[0]),sdc_sha256=sha(self.base/FILES[1]),spef_sha256=sha(self.base/FILES[2]),worst_slack_ps=270.7)
  self.record=dict(setup_ss=row,hold_ff=dict(row,worst_slack_ps=-.85))
  self.plan=make_plan(self.base,'ew',self.record)
 def test_exact_inventory_and_area(self):
  validate(self.plan)
  self.assertEqual(len(endpoints()),128)
  self.assertEqual(sum(len(r['cells'])for r in self.plan['patches']),384)
  self.assertAlmostEqual(self.plan['area_added_um2'],27.9936)
 def test_reject_bad_inventory_or_cells(self):
  for mutate in [lambda p:p['patches'].pop(),lambda p:p['patches'][0].update(endpoint=p['patches'][1]['endpoint']),lambda p:p['patches'][0].update(cells=['INVx1_ASAP7_75t_R']*3),lambda p:p.update(cycles_added=1)]:
   p=copy.deepcopy(self.plan);mutate(p)
   with self.assertRaises(ValueError):validate(p)
 def test_immutable_constraints_and_fresh_scripts(self):
  out=self.root/'candidate';prepare(self.base,out,self.plan)
  self.assertEqual((out/'6_final.sdc').read_bytes(),(self.base/'6_final.sdc').read_bytes())
  self.assertIn('set_dont_touch',(out/'patch.tcl').read_text())
  self.assertNotIn('repair_timing -',(out/'patch.tcl').read_text())
  for c in ('ss','ff'):
   text=(out/f'sta_{c}.tcl').read_text()
   self.assertIn(str(out)+'/6_final.odb',text)
   self.assertIn('/RESETN',text)
   self.assertNotIn('set_clock_uncertainty',text)
  with self.assertRaises(ValueError):prepare(self.base,out,self.plan)
 def test_hash_pinning(self):
  (self.base/FILES[0]).write_text('changed')
  with self.assertRaises(ValueError):prepare(self.base,self.root/'candidate',self.plan)
  with self.assertRaises(ValueError):make_plan(self.base,'ew',self.record)
 def test_fresh_receipt_fail_closed(self):
  text='OT_WS 2e-11\n'+'\n'.join(f'HBM_TARGET endpoint={e} slack=20'for e in endpoints())
  self.assertEqual(parse_timing(text)['worst_slack_ps'],20)
  for bad in [text.replace('slack=20','slack=INF',1),text+'\nHBM_TARGET endpoint='+endpoints()[0]+' slack=20',text.replace('OT_WS','MISSING')]:
   with self.assertRaises(ValueError):parse_timing(bad)
if __name__=='__main__':unittest.main()
