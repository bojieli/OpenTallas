import unittest
from ref_tile import fill_check

class LatticeChannelFillTest(unittest.TestCase):
    def spec(self):
        return {"kind":"tile", "macros":[{}]*10, "fill_reason":{"lattice_channel_bound":{
            "why":"ROOT approved measured lattice/channel geometry", "approved_by":"ROOT",
            "std_band_y_um":[216,259.2]}}}
    def blocks(self):
        return [{"kind":"macro","x":x,"y":y,"w":174.12,"h":29.736}
                for x in (43.2,259.2) for y in (43.2,129.6,302.4,388.8,475.2)]
    def check_fill(self,s=None,b=None,area=10495.7):
        return fill_check(s or self.spec(),475.2,561.6,self.blocks() if b is None else b,area)
    def test_actual_geometry_warns(self):
        result=self.check_fill(); self.assertEqual(result[0],"WARN")
        self.assertIn("gate-rule exception",result[2])
    def test_missing_approval_fails(self):
        s=self.spec();del s["fill_reason"]["lattice_channel_bound"]["approved_by"]
        self.assertEqual(self.check_fill(s)[0],"FAIL")
    def test_claim_without_blocks_fails(self):
        self.assertEqual(self.check_fill(b=[])[0],"FAIL")
    def test_off_lattice_fails(self):
        b=self.blocks();b[0]["x"]+=0.432;self.assertEqual(self.check_fill(b=b)[0],"FAIL")
    def test_squeezed_channel_fails(self):
        b=self.blocks();b[1]["y"]=86.4;self.assertEqual(self.check_fill(b=b)[0],"FAIL")
    def test_band_over_macro_fails(self):
        s=self.spec();s["fill_reason"]["lattice_channel_bound"]["std_band_y_um"]=[100,143.2]
        self.assertEqual(self.check_fill(s)[0],"FAIL")
    def test_actual_band_density_fails(self):
        self.assertEqual(self.check_fill(area=16000)[0],"FAIL")

if __name__ == "__main__": unittest.main()
