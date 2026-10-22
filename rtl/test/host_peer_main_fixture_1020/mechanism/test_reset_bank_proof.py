import copy,json,unittest
from reset_bank_proof import equivalence,Refused,exhaustive_maturity

def bank(base):
 return {str(base+i):{"type":"$_DFF_PN0_","connections":{"C":[90],"R":[91],"D":["1" if i==0 else base+i-1],"Q":[base+i]}} for i in range(3)}

class Proof(unittest.TestCase):
 def setUp(self):self.c=bank(10)|bank(20)
 def test_identical_after_assert(self):self.assertTrue(equivalence(self.c,12,22,True))
 def test_cold_refusal(self):
  with self.assertRaisesRegex(Refused,"cold state"):equivalence(self.c,12,22)
 def test_exhaustive_arbitrary_cold_and_assert(self):self.assertEqual(exhaustive_maturity()["cold_output_mismatches"],32)
 def test_clock_mutant(self):
  self.c["20"]["connections"]["C"]=[92]
  with self.assertRaises(Refused):equivalence(self.c,12,22,True)
 def test_reset_mutant(self):
  self.c["21"]["connections"]["R"]=[92]
  with self.assertRaises(Refused):equivalence(self.c,12,22,True)
 def test_latency_mutant(self):
  self.c["22"]["connections"]["D"]=[20]
  with self.assertRaises(Refused):equivalence(self.c,12,22,True)
 def test_enable_mutant(self):
  self.c["21"]["connections"]["E"]=[93]
  with self.assertRaises(Refused):equivalence(self.c,12,22,True)
 def test_init_mutant(self):
  self.c["21"]["init"]="1"
  with self.assertRaises(Refused):equivalence(self.c,12,22,True)
 def test_cycle_mutant(self):
  self.c["21"]["connections"]["D"]=[22]
  with self.assertRaises(Refused):equivalence(self.c,12,22,True)
 def test_reset_value_mutant(self):
  self.c["21"]["type"]="$_DFF_PN1_"
  with self.assertRaises(Refused):equivalence(self.c,12,22,True)
 def test_chain_root_mutant(self):
  self.c["20"]["connections"]["D"]=["0"]
  with self.assertRaises(Refused):equivalence(self.c,12,22,True)
if __name__=="__main__":
 print(json.dumps(exhaustive_maturity(),sort_keys=True));unittest.main()
