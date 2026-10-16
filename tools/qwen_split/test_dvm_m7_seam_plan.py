import copy
import unittest
import dvm_m7_seam_plan as P

class SeamContract(unittest.TestCase):
    def test_actual_two_phase_shapes(self):
        for phase,origin in [(0,1002240),(32,479520)]:
            self.assertEqual(P.audit(P.plan(phase),[origin]),[])
    def test_wrong_phase_alias_rejected(self):
        self.assertTrue(P.audit(P.plan(0),[479520]))
        self.assertTrue(P.audit(P.plan(32),[1002240]))
    def test_missing_payload_and_renamed_bit_rejected(self):
        p=P.plan(0);p['ports'].pop();self.assertTrue(P.audit(p,[0]))
        p=P.plan(0);p['ports'][0]['names']['head_N']='tied_or_absent'
        self.assertTrue(P.audit(p,[0]))
    def test_unbounded_contact_rejected(self):
        p=P.plan(0);p['ports'][0]['edge_depth_nm']=1000
        self.assertTrue(P.audit(p,[0]))
if __name__=='__main__':unittest.main()
