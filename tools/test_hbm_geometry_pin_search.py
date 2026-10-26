import unittest
from hbm_geometry_pin_search import search
from hbm_geometry_coverage import audit

def child(name,x,y,w=10,h=10):
 return dict(instance=name,xy_um=[x,y],outline_um=[w,h],pins={p:dict(shapes=[dict(rect_um=[x,y,x,y])]) for p in ['i','o']})
def net(name,driver,load):
 return dict(net=name,kind='signal',endpoints=[dict(instance=driver,port='o',lsb=0,width=1,direction='output'),dict(instance=load,port='i',lsb=0,width=1,direction='input')])
class GeometrySearchTest(unittest.TestCase):
 def test_external_anchor_and_all_incident_wires(self):
  m=dict(component='test',component_sha256='x',outline_um=[200,100],children=[child('a',0,0),child('b',100,0),child('c',120,0)],connections=[net('ab','a','b'),net('bc','b','c'),dict(net='external',kind='signal',endpoints=[dict(instance='a',port='i',lsb=0,width=1,direction='input')])])
  r=search(m);self.assertNotIn('a',r['placement_deltas_um']);self.assertEqual(r['actual_bit_pairs'],2);self.assertLess(r['after']['total_bit_um'],r['before']['total_bit_um']);self.assertLessEqual(r['after']['max_pin_manhattan_um'],r['before']['max_pin_manhattan_um'])
 def test_explicit_boundary_binding_stays_fixed_with_internal_fanout(self):
  m=dict(component='test',component_sha256='x',outline_um=[200,100],children=[child('a',0,0),child('b',100,0),child('c',120,0)],connections=[net('ab','a','b'),net('bc','b','c')],boundary_binding=[dict(parent_port='output',child_instance='b')]);r=search(m);self.assertNotIn('b',r['placement_deltas_um']);self.assertIn('b',r['external_data_anchored_children'])
 def test_obstacle_cannot_be_crossed(self):
  m=dict(component='test',component_sha256='x',outline_um=[100,10],children=[child('a',0,0),child('b',20,0),child('wall',10,0)],connections=[net('ab','a','b')]);r=search(m);self.assertEqual(r['placement_deltas_um'],{})
 def test_full_sm_frame_not_child_bbox_and_master_mismatch(self):
  c=dict(instances={'sm0':dict(master='new')},known_actual_edges=[])
  old=dict(full_repack_candidate=dict(instances={'sm0':['old','sm',0,0,10,10,'R0'],'obstacle':['o','other',15,0,10,10,'R0']}))
  r=audit(c,old,dict(frame_outline_um=[20,20],children=[]));self.assertEqual(r['coverage']['changed_master_names'],['sm0']);self.assertEqual(len(r['sm_replacement']['collisions_after_replacement']),1);self.assertEqual(r['sm_replacement']['actual_component_outline_um'],[20,20])
 def test_missing_actual_pin_is_error(self):
  a=child('a',0,0);a['pins'].pop('o');m=dict(component='test',component_sha256='x',outline_um=[100,10],children=[a,child('b',20,0)],connections=[net('ab','a','b')]);self.assertRaises(ValueError,search,m)
if __name__=='__main__':unittest.main()
