import itertools,sys,unittest
from fractions import Fraction as F
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import dsrom_c9_global_domain_assessment as d
class Domains(unittest.TestCase):
 def task(self,source,sink,n,b=2.88):
  return dict(source_contact_DBU=source,sink_contact_DBU=sink,node_ids=list(range(n)),first_metal_budget_fF=b)
 def test_two_ended_box_keeps_every_small_exact_feasible_chain(self):
  rc={'M8':1.,'M9':1.};t=self.task([0,0],[642,0],2,0.1)
  points=[(x,y) for x in (-50,0,50,271,321,371) for y in (-50,0,50)]
  checked=0
  for a,b in itertools.product(points,repeat=2):
   edge=lambda x,y:sum(abs(x[i]-y[i]) for i in (0,1))/1000
   if edge([0,0],a)<=0.1 and edge([a[0]+321,a[1]],b)<=2.88 and edge([b[0]+321,b[1]],[642,0])<=2.88:
    for j,p in enumerate((a,b)):
     box=d.node_box(t,j,rc);self.assertTrue(box[0]<=p[0]<=box[2] and box[1]<=p[1]<=box[3])
    checked+=1
  self.assertGreater(checked,0)
 def problem(self,sites,tasks):
  return dict(shard=0,sites=[dict(bbox_DBU=[x-27,y-135,x+351,y+135]) for x,y in sites],tasks=tasks,node_count=sum(len(t['node_ids']) for t in tasks),RC_fF_per_um={'M8':1.,'M9':1.})
 def test_shared_actual_site_prevents_independent_branch_split_and_gives_hall_witness(self):
  t=self.task([0,0],[321,0],1,0.01);u=dict(t,node_ids=[1]);m,_=d.assess(self.problem([(0,0)],[t,u]))
  self.assertEqual(len(m['conservative_components']),1);self.assertEqual(m['component_Hall_deficits'][0]['nodes'],2)
 def test_disjoint_domains_allow_components_without_dropping_nodes(self):
  t=self.task([0,0],[321,0],1,0.01);u=self.task([10000,0],[10321,0],1,0.01);u['node_ids']=[1]
  m,_=d.assess(self.problem([(0,0),(10000,0)],[t,u]));self.assertEqual(len(m['conservative_components']),2);self.assertFalse(m['unsat_witness_found'])
 def test_impossible_direct_edge_retained(self):
  t=self.task([0,0],[321,0],1,0.01);u=self.task([0,0],[10000,0],0,0.1)
  m,_=d.assess(self.problem([(0,0)],[t,u]));self.assertEqual(len(m['direct_edge_failures']),1)
 def test_empty_two_ended_domain_is_recorded_not_selected_placement(self):
  t=self.task([0,0],[321,0],1,0.01);m,_=d.assess(self.problem([(10000,0)],[t]))
  self.assertEqual(len(m['rectangular_domain_empty_witnesses']),1)
if __name__=='__main__':unittest.main()
