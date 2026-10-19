import unittest
from ref_tile import fill_check

class LatticeChannelFillTest(unittest.TestCase):
    def spec(self):
        return {"kind":"tile", "macros":[{}]*4, "fill_reason":{"lattice_channel_bound":{
            "why":"ROOT approved measured lattice/channel geometry", "lattice_um":43.2,
            "min_channel_um":41.88, "std_band_util":0.516}}}
    def test_measured_structural_reason_warns(self):
        result=fill_check(self.spec(),475.2,561.6,[],10495.7)
        self.assertEqual(result[0],"WARN")
        self.assertIn("lattice/channel-bound",result[2])
    def test_missing_measurement_still_fails(self):
        spec=self.spec(); del spec["fill_reason"]["lattice_channel_bound"]["std_band_util"]
        self.assertEqual(fill_check(spec,475.2,561.6,[],10495.7)[0],"FAIL")
    def test_overfull_cell_band_still_fails(self):
        spec=self.spec();spec["fill_reason"]["lattice_channel_bound"]["std_band_util"]=0.8
        self.assertEqual(fill_check(spec,475.2,561.6,[],10495.7)[0],"FAIL")

if __name__ == "__main__": unittest.main()
