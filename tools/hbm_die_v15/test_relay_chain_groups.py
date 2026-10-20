import unittest
from relay_chain_groups import linear_chains

class ChainGroups(unittest.TestCase):
 def checked(self,nodes,pred,succ):
  out=list(linear_chains(nodes,pred,succ));flat=[n for chain in out for n in chain]
  self.assertCountEqual(flat,nodes);self.assertEqual(len(flat),len(set(flat)))
  return out
 def test_fanout_starting_branch_cannot_be_lost(self):
  # Old algorithm: start B, walk back to A, follow overwritten A->C; B never placed.
  out=self.checked(['B','A','C'],{'B':'A','C':'A'},{'A':'C'})
  self.assertEqual(out,[['B'],['A','C']])
 def test_fanin_does_not_follow_another_parent(self):
  out=self.checked(['A','B','C'],{'C':'B'},{'A':'C','B':'C'})
  self.assertEqual(out,[['A'],['B','C']])
 def test_linear_reverse_input_still_groups(self):
  self.assertEqual(self.checked(['C','B','A'],{'B':'A','C':'B'},{'A':'B','B':'C'}),[['A','B','C']])
 def test_cycle_terminates_and_covers_each_once(self):
  out=self.checked(['A','B','C'],{'A':'C','B':'A','C':'B'},{'A':'B','B':'C','C':'A'})
  self.assertEqual(len(out),1)
 def test_outside_endpoints_and_singletons(self):
  self.assertEqual(self.checked(['A','B'],{'A':'source'},{'B':'sink'}),[['A'],['B']])

if __name__=='__main__':unittest.main()
