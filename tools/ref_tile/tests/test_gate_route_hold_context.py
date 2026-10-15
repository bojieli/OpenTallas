"""Run rendered gate environment against production job settings; no physical runs."""
import json,os,pathlib,re,subprocess,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
import ref_tile as R
import pre_route_gate as G
class RouteHoldParity(unittest.TestCase):
 def spec(self,**kw):
  s=dict(name='sample',top='top',kind='tile',sources=[],clock_port='clk',params={},route=dict(hold_margin_ns=.03),children=[],macros=[],pins={},reset_ports=[]);s.update(kw);return s
 def executed(self,s):
  sh=G.gate_route_clock_hooks('export OT_ORFS_CORNER_OVERRIDE=TC\n',s)
  sh=G.gate_route_hold_context(sh,s,'physical/ref_tile/sample')
  keys=['HM','OT_ROUTE_HOLD_CORNERS','OT_MM_FF_SDC','OT_CTS_FIX_HOOKS']
  sh+='python3 -c '+__import__('shlex').quote('import os,json;print(json.dumps({k:os.environ.get(k) for k in '+repr(keys)+'}))')
  env=dict(os.environ,HM='0.001',OT_ROUTE_HOLD_CORNERS='primary',OT_CTS_FIX_HOOKS='wrong')
  return json.loads(subprocess.check_output(['bash','-c',sh],env=env,text=True))
 def test_recipe2_actual_30ps_mm_not_shell_fallback(self):
  s=self.spec();d=self.executed(s);j=R.gen_job(s,'physical/ref_tile/sample','deadbeef',[])
  self.assertEqual(d['HM'],'0.03');self.assertEqual(j['route_hold_margin_ns'],.03)
  self.assertIn("HM=0.03 OT_MM_FF_SDC='"+d['OT_MM_FF_SDC']+"'",j['stages']['route']['cmd'])
  self.assertEqual(d['OT_ROUTE_HOLD_CORNERS'],j['route_hold_corners']);self.assertEqual(d['OT_CTS_FIX_HOOKS'],R.clock_fix_hooks(s))
 def test_explicit_legacy_margin_preserved(self):
  s=self.spec();s['route']['hold_margin_ns']=.01;self.assertEqual(self.executed(s)['HM'],'0.01')
 def test_boundary_repair_sdc_selected_exactly_as_route(self):
  s=self.spec();s['route']['io_hold_margin_ns']=.02;d=self.executed(s)
  self.assertTrue(d['OT_MM_FF_SDC'].endswith('/signoff_ffrepair.sdc'))
  self.assertIn(d['OT_MM_FF_SDC'],R.gen_job(s,'physical/ref_tile/sample','deadbeef',[])['stages']['route']['cmd'])
 def test_multiroot_keeps_one_boundary_owner(self):
  s=self.spec(clock='multiple_cts_roots');d=self.executed(s)
  self.assertNotIn('link_budget_hook.tcl',d['OT_CTS_FIX_HOOKS']);self.assertEqual(d['HM'],'0.03');self.assertEqual(d['OT_ROUTE_HOLD_CORNERS'],'mm')
 def test_missing_insertion_marker_fails_closed(self):
  with self.assertRaises(ValueError):G.gate_route_hold_context('changed',self.spec(),'kit')

 def test_hybrid_tile_native_boundary_and_cluster_budget_remain_distinct(self):
  tile=self.spec(clock='hybrid_entries');d=self.executed(tile)
  cmd=R.gen_job(tile,'physical/ref_tile/sample','deadbeef',[])['stages']['route']['cmd']
  self.assertNotIn('link_budget_hook.tcl',d['OT_CTS_FIX_HOOKS']);self.assertNotIn('link_budget_hook.tcl',cmd)
  self.assertEqual(len(d['OT_CTS_FIX_HOOKS'].split()),2)
  cluster=self.spec(clock='hybrid_entries',kind='cluster');d=self.executed(cluster)
  cmd=R.gen_job(cluster,'physical/ref_tile/sample','deadbeef',[])['stages']['route']['cmd']
  self.assertIn('link_budget_hook.tcl',d['OT_CTS_FIX_HOOKS']);self.assertIn('link_budget_hook.tcl',cmd)
  self.assertEqual(len(d['OT_CTS_FIX_HOOKS'].split()),3)
