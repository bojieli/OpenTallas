import importlib.util,unittest,pathlib
from unittest.mock import patch
sp=importlib.util.spec_from_file_location('sta',str(pathlib.Path(__file__).resolve().parents[2]/'tools/die_plan/die_sta_related.py'));m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
class Test(unittest.TestCase):
 def test_repeated_cli(self):self.assertEqual(m.parse_core_views(['X=a','X=b','Y=c','X=a']),{'X':['a','b'],'Y':'c'})
 def test_select_signed_view(self):
  a={'meta':{'view_dir':'a'}};b={'meta':{'view_dir':'b'}}
  with patch.object(m,'pins_relation',side_effect=[('mirror:R180',None),('canonical',None)]):self.assertIs(m.select_core_view('X',[a,b],'pins','.',[],[],True)[0],b)
 def test_ambiguity(self):
  with patch.object(m,'pins_relation',return_value=('canonical',None)):
   with self.assertRaisesRegex(ValueError,'ambiguous'):m.select_core_view('X',[{'meta':{}},{'meta':{}}],'pins','.',[],[],True)
 def test_unmatched(self):
  with patch.object(m,'pins_relation',return_value=(None,'pins differ')):self.assertEqual(m.select_core_view('X',[{'meta':{}}],'pins','.',[],[],True),(None,None,'pins differ'))
 def test_unmatched_abi(self):
  a={'meta':{}}
  self.assertEqual(m.select_core_view('X',[a],None,None,None,[],False),(a,None,None))
  with self.assertRaises(ValueError):m.select_core_view('X',[a,a],None,None,None,[],False)
class Coverage(unittest.TestCase):
 def test_build_preserves_single_and_counts_multiple(self):
  plan={'partitions':[]};taps={'p':{'part':'A'}}
  def model(module,d,*args):return {'meta':{'view_dir':d},'etm':{'source':d}}
  for spec,keys in [('a',['X']),(['a','b'],['X@1','X@2'])]:
   with patch.object(m,'core_view_model',side_effect=model), patch.object(m,'budget_model',return_value={'budget':1}), patch.object(m,'map_cores_to_taps',return_value={('A','u'):('X','p',1,'pins')}), patch.object(m,'core_outlines',return_value={}), patch.object(m,'pins_relation',side_effect=lambda meta,*a: ('canonical',None) if meta['view_dir']=='a' else (None,'different')):
    views,cov=m.build_views(plan,taps,'TT',None,None,{'X':spec},{},0,0,True,'.')
    self.assertEqual(cov['core_instances_real'],1);self.assertEqual(cov['real_by_module'],{'X':1});self.assertEqual(list(cov['core_models']),keys);self.assertEqual(views['p'][1]['meta']['view_dir'],'a')
unittest.main()
