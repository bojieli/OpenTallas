import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import dsrom_c9_native_clock_constraints as n
class NativeContacts(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.grid=n.B.load(n.BASE/'inputs/grid.json')
  cls.lef=n.B.lef_masters('\n'.join(n.B.load(n.B.OLD/'inputs/cell_LEF.json.gz').values()))
  cls.m=n.B.load(n.BASE/'model.json')
 def test_actual_phase_sets_exclude_centroid135(self):
  phases=n.phases(self.grid,'M2','Y');self.assertEqual(sorted(v[0] for v in phases),[0,45,81,117,153,189,225])
  self.assertFalse(any((135-o)%p==0 for o,p in phases));self.assertEqual(n.phases(self.grid,'M3','X'),[(9,36)])
 def test_literal_via_master_and_enclosure_every_candidate(self):
  for key,c in self.m['cases'].items():
   self.assertGreater(c['enclosed_phase_compatible_contact_count'],0)
   for p in c['contacts']:
    rr=p['literal_pin'];entry=p.get('native_entry_layer','M1')
    via=next(q['bbox_DBU'] for q in p['shapes'] if q.get('via')==('VIA12' if entry=='M1' else 'VIA23') and q['layer']==entry)
    self.assertEqual([via[2]-via[0],via[3]-via[1]],[18,22] if entry=='M1' else [28,18])
    pad=next(q['bbox_DBU'] for q in p['shapes'] if q.get('role')=='vertical_landing_minarea')
    self.assertGreaterEqual((pad[2]-pad[0])*(pad[3]-pad[1]),666)
    self.assertTrue(rr[0]<=via[0] and rr[1]<=via[1] and rr[2]>=via[2] and rr[3]>=via[3])
    y=p['pin_point_DBU'][1];self.assertTrue(any((y-o)%pitch==0 for o,pitch in n.phases(self.grid,'M2','Y')))
    x=p['M3_endpoint_DBU'][0];self.assertEqual((x-9)%36,0)
 def test_translated_master_OBS_can_reject_a_previously_legal_contact(self):
  import copy
  master=copy.deepcopy(self.lef[n.B.BUF]);item=dict(instance='t',master=n.B.BUF,bbox_DBU=[0,0,378,270],orientation='R0')
  ports=n.native_ports(item,'A',master,self.grid);self.assertTrue(ports)
  for q in ports:master['OBS'].append(dict(layer='M2',bbox_DBU=next(r['bbox_DBU'] for r in q['shapes'] if r['layer']=='M2' and r.get('role')=='horizontal_access_minarea')))
  self.assertEqual(n.native_ports(item,'A',master,self.grid),[])
 def test_both_orientation_and_site_phases_not_only_one_dummy_cell(self):
  self.assertEqual(len(self.m['cases']),24)
  for pin,counts in [('A',[4]),('Y',[6])]:
   rows=[v['enclosed_phase_compatible_contact_count'] for k,v in self.m['cases'].items() if k.startswith(n.B.BUF+'.'+pin)]
   self.assertEqual(set(rows),set(counts));self.assertEqual(len(rows),4)
 def test_contact_model_is_not_global_qualification(self):
  self.assertFalse(self.m['physical_build_admitted']);self.assertFalse(self.m['new_architecture_parameter'])
  self.assertEqual(self.m['new_clock_or_capture_cycles'],0)
  self.assertIn('Full master-neighbor',self.m['scope'])
if __name__=='__main__':unittest.main()
