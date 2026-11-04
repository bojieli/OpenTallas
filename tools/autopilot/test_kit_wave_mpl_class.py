import os,sys,unittest
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import kit_wave as K
class T(unittest.TestCase):
    def test_mpl0034_with_watchdog_143_is_plan(self):
        t="[ERROR MPL-0034] Cannot place u_bound.u_core.u_ptx at (1, 2) (3, 4), outside of the core\nError: macro_place.tcl, 6 MPL-0034\nmake: *** Error 2\not-run: RAN on intel1 (unit x): exit 143\nKW_PLACE_RC=143\n"
        c,r=K.classify("place",t); self.assertEqual(c,"PLAN",r); self.assertIn("MPL-0034",r)
    def test_plain_143_stays_infra(self):
        c,r=K.classify("place","KIT_PREFLIGHT PASS issues 0\not-run: RAN on intel1 (unit x): exit 143\nKW_PLACE_RC=143\n")
        self.assertEqual(c,"INFRA",r)
if __name__=="__main__": unittest.main()
