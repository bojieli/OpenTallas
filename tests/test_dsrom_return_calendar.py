"""Source-derived tag/tree identities and unified resource pins, no HDL execution."""
import importlib.util,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import model_dsrom_return_calendar as M
class ReturnTests(unittest.TestCase):
 def test_reproduction(self):
  self.assertEqual(M.generate(),json.loads((M.OUT/'model.json').read_text()))
 def test_full_counts_area_and_fault_indices(self):
  d=M.generate();r=d['unified_resource_ledger'];f=d['source_fault_vector_diagnosis']
  self.assertEqual(138469120,r['declared_storage_lower_bound_bits']);self.assertEqual(2121600,r['node_all_link_bits_per_cycle'])
  self.assertAlmostEqual(40.377595392,r['register_implementation_proxy_mm2'])
  driven=set()
  for a,b in f['node_index_ranges']:driven.update(range(a,b+1))
  self.assertEqual(set(range(16256)),driven);self.assertEqual(set(range(16256,16383)),set(range(16384))-driven-{16383})
 def test_installed_corners(self):
  d=json.loads((M.OUT/'installed_ICG_arcs.json').read_text())
  for c in ('SS','FF'):
   self.assertEqual('1ps',d[c]['time_unit'])
   self.assertEqual(M.h((M.OUT/('ICG_'+c+'_installed.lib')).read_bytes()),d[c]['cell_sha256'])
   self.assertEqual(2,len([a for a in d[c]['ENA'] if a['type']=='hold_rising']))
  self.assertTrue(M.generate()['installed_ICG_closure_addendum']['SS_library_hash_matches_retained_worker'])
 def test_all_legal_segment_tag_tree_shapes(self):
  # Independent balanced padded symbolic tree. Padding elision requires the source's
  # finite canonical+0 identity contract; this test proves structure, not FP32 values.
  def gold(a):
   if len(a)==1:return a[0]
   k=len(a)//2;l=gold(a[:k]);r=gold(a[k:])
   return l if r is None else (r if l is None else (l,r))
  def norm(lo,k,n):
   for _ in range(5):
    if not(lo==0 and (1<<k)>=n) and not((lo>>k)&1) and lo+(1<<k)>=n:k+=1
   return lo,k
  for n in range(1,32):
   width=1<<(n-1).bit_length();expected=gold([('leaf',i) for i in range(n)]+[None]*(width-n))
   for order in (list(range(n)),list(reversed(range(n))),list(range(0,n,2))+list(range(1,n,2))):
    a=[(*norm(i,0,n),('leaf',i)) for i in order]
    while len(a)>1:
     hit=None
     for i,x in enumerate(a):
      for j,y in enumerate(a):
       if i<j and x[1]==y[1] and x[0]^y[0]==1<<x[1]:hit=(i,j);break
      if hit:break
     self.assertIsNotNone(hit,(n,order,a));i,j=hit;x,y=a[i],a[j]
     left,right=sorted((x,y),key=lambda t:t[0]);lo,k=norm(left[0],left[1]+1,n)
     a=[x for t,x in enumerate(a) if t not in hit]+[(lo,k,(left[2],right[2]))]
    self.assertEqual(expected,a[0][2]);self.assertEqual(0,a[0][0]);self.assertGreaterEqual(1<<a[0][1],n)
 def test_no_launch_or_retiming_claim(self):
  d=M.generate();self.assertFalse(any(d['execution'][k] for k in ('HDL','STA','PNR')))
  self.assertTrue(d['drain_and_clock_contract']['no_silent_stage_or_clock_change'])
 def test_unified_extension_defaultoff_and_no_double_count(self):
  import uarch_model_dsrom_return_prepare as P
  base=M.U.area_ledger(M.U.BASE)
  self.assertEqual(base,P.area_ledger(M.U.BASE))
  full=P.area_ledger(M.U.BASE,actual_return=True)
  self.assertAlmostEqual(16384*M.U.UNIT['fp32_add_um2']/1e6,full['return_adders'])
  self.assertAlmostEqual(base['rom_field_strip_used_mm2']-base['return_adders']+full['return_adders']+full['return_storage_register_proxy'],full['rom_field_strip_used_mm2'])
  with self.assertRaisesRegex(ValueError,'full-target'):P.area_ledger(M.U.BASE,actual_return=True,NP=16)
if __name__=='__main__':unittest.main()
