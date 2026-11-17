import copy
import importlib.util
import tempfile
import unittest
from pathlib import Path
P=Path(__file__).with_name('frame_visibility_profile.py')
s=importlib.util.spec_from_file_location('vprof',P);v=importlib.util.module_from_spec(s);s.loader.exec_module(v)


def fixture():
 st=dict(inputs={'xs':[['x',2]]},control={'go':[['x',3]],'cfg_v':[['x',3]],'go_tag':[['x',1]]})
 b=dict(stations={'e0':st},nodes={'n0':{'a':[['e0.r0',1]],'b':[['e0.r1',2]]}},root=[['n0',4]],links={'seam lpl_11 u_r0->r1':[3]})
 n=copy.deepcopy(b)
 for labels in list(n['stations']['e0']['inputs'].values())+list(n['stations']['e0']['control'].values()):labels[0][1]+=2
 n['root'][0][1]+=3;n['links']['seam lpl_11 u_r0->r1'][0]+=2
 return b,n


class Profiles(unittest.TestCase):
 def test_exact_per_interface_and_stale_control(self):
  b,n=fixture();p=v.build(b,n,cohort='p1',top='col_h10_l4_lp_asb_x',source_sha256={},partition_types=['p1'])
  self.assertEqual(v.apply(b,p),n);self.assertEqual(b['root'][0][1],4)
  self.assertEqual(v.link_delta(p,'seam lpl_11 u_r0->r1'),2)
  stale=copy.deepcopy(b);stale['stations']['e0']['control']['go_tag'][0][1]+=1
  with self.assertRaises(ValueError):v.apply(stale,p)
  bad=copy.deepcopy(n);bad['stations']['e0']['control']['go_tag'][0][1]-=1
  with self.assertRaises(ValueError):v.build(b,bad,cohort='p1',top='col_h10_l4_lp_asb_x',source_sha256={},partition_types=['p1'])

 def test_only_explicit_matching_source_and_plan_cohort(self):
  b,n=fixture()
  with tempfile.TemporaryDirectory() as root:
   f=Path(root)/'native.sv';f.write_text('native source')
   p=v.build(b,n,cohort='p1',top='col_h10_l4_lp_asb_x',source_sha256={'native.sv':v.digest(f)},partition_types=['p1'])
   plan=dict(partition_types={'p1':dict(contents=[dict(module=p['band_module'],params={'COLRELAY_P1':1})]),'p0':dict(contents=[dict(module=p['band_module'],params={})])},partitions=[{'type':'p1'},{'type':'p0'}])
   v.validate_selection(p,root,plan,'p1',p['top'])
   for mutant in ['wrongcohort','off','extra','missingband','source']:
    pp=copy.deepcopy(plan);cohort='p1'
    if mutant=='wrongcohort':cohort='p0'
    if mutant=='off':pp['partition_types']['p1']['contents'][0]['params']['COLRELAY_P1']=0
    if mutant=='extra':pp['partition_types']['p0']['contents'][0]['params']['COLRELAY_P1']=1
    if mutant=='missingband':pp['partition_types']['p1']['contents']=[]
    if mutant=='source':f.write_text('changed')
    with self.assertRaises(ValueError,msg=mutant):v.validate_selection(p,root,pp,cohort,p['top'])


if __name__=='__main__':unittest.main()
