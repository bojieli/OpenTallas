"""Actual r51 TREQ joins a command lane with measured E_sta7 and hold facts."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import record_bundles as RB
import lane_groups as LG

class TreqPadding(unittest.TestCase):
    def rows(self,pads):
        return [dict(bid=b,src="tt_ctlm",dst="dvs_W5",bundle="DV.treq.ctlm",
                     n=n+pads.get(b,0),E_sta=es,E=RB.fwd_e_est(n+pads.get(b,0))+es-2)
                for b,n,es in [("cmd",26,7),("treq",24,2)]]
    def test_measured_command_keeps_age_new_request_gets_stations(self):
        h={"cmd":{"tt":4871.4,"ff":3589.1}}
        pads=RB.frame_pads({"cmd":"b","treq":"b"},{"cmd":26,"treq":24},{"cmd":7,"treq":2},4,h0=h)
        self.assertNotIn("cmd",pads)
        self.assertEqual(pads,{"treq":10})
        rows=self.rows(pads);LG.equalize(rows,4,h0=h)
        self.assertEqual([r["E"] for r in rows],[19,19])
        self.assertEqual([r["E_sta"] for r in rows],[7,3])
    def test_missing_measured_facts_does_not_waive_ring_window(self):
        pads=RB.frame_pads({"cmd":"b","treq":"b"},{"cmd":26,"treq":24},{"cmd":7,"treq":2},4)
        with self.assertRaises(ValueError):LG.equalize(self.rows(pads),4)
    def test_insufficient_actual_hold_fails(self):
        with self.assertRaisesRegex(ValueError,"measured landing hold fails"):
            RB.frame_pads({"cmd":"b","treq":"b"},{"cmd":26,"treq":24},{"cmd":7,"treq":2},4,h0={"cmd":{"tt":500.,"ff":500.}})
    def test_partial_corner_facts_fail(self):
        with self.assertRaisesRegex(ValueError,"TT/FF"):
            RB.frame_pads({"cmd":"b","treq":"b"},{"cmd":26,"treq":24},{"cmd":7,"treq":2},4,h0={"cmd":{"tt":4871.4}})

if __name__=="__main__":unittest.main()
