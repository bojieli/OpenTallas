import unittest
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from ft_reach_legalizer import ReachAllocator
import ft_joint_siting as J
class Joint(unittest.TestCase):
 def execute(self,reach,rows,seed_fail=False,terminal=None):
  a=ReachAllocator((0,0,10,rows),cell_size=(1,1),column_pitch=1,row_pitch=1,origin=(0,0));a.reserve_rectangle((0,0,1,1));saved=set(a.used)
  if terminal is not None:a.terminal_goals={('f',b):terminal for b in range(2)}
  s=dict(name='f',width=1,stations=2,in_face='W',out_face='E');pins={'f_i':{b:(-.5,.5,'W')for b in range(2)},'f_o':{b:(9.5,.5,'E')for b in range(2)}}
  old=J.F._move
  def seed(*args):
   if seed_fail:raise SystemExit('conservative seed guard')
   return 0
  J.F._move=seed
  try:r=J.slot(s,2,pins,[],[],[],reach,reach,a,'t','f',2)
  finally:J.F._move=old
  return a,saved,s,r
 def test_failed_slot_rolls_back_only_its_new_rows(self):
  a,saved,s,r=self.execute(4,1);self.assertIn('infeasible',r);self.assertEqual(a.used,saved);self.assertNotIn('bit_sites_um',s)
 def test_success_materializes_all_bits_and_stages(self):
  a,saved,s,r=self.execute(5,2);self.assertNotIn('infeasible',r);self.assertEqual(len(s['bit_sites_um'][0]),2);self.assertEqual(len(a.used)-len(saved),2);self.assertLessEqual(r['max_bit_hop_um'],5)
 def test_seed_guard_does_not_replace_actual_row_proof(self):
  a,saved,s,r=self.execute(5,2,True);self.assertNotIn('infeasible',r);self.assertEqual(r['geometry_seed_failure'],'conservative seed guard');self.assertLessEqual(r['max_bit_hop_um'],5)
 def test_actual_capture_goal_overrides_output_proxy(self):
  a,saved,s,r=self.execute(5,2,terminal=(12,.5));self.assertIn('infeasible',r);self.assertEqual(a.used,saved)
if __name__=='__main__':unittest.main()
