import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import form_geometry as F


class FormGeometryTests(unittest.TestCase):
    def test_parent_growth_checks_real_macro_and_mx_bbox(self):
        p = dict(outline_um=[1442.88,1226.88], hard_cores=[
            dict(inst="lane",origin_um=[8.64,129.6],outline_um=[295.92,444.96],orient="R0",obs_max="M5"),
            dict(inst="land",origin_um=[95.04,596.16],outline_um=[112.32,112.32])])
        self.assertTrue(F.fit_core(p,"lane")["fits"])
        tall = F.fit_core(p,"lane",[295.92,660.96],obs_max="M6")
        self.assertFalse(tall["fits"])
        self.assertEqual(tall["collisions"][0]["name"],"land")
        self.assertEqual(tall["new_obstruction_layers"],["M6"])
        p["hard_cores"][0].update(origin_um=[8.64,648],orient="MX")
        tall = F.fit_core(p,"lane",[295.92,660.96])
        self.assertAlmostEqual(tall["outside_um"]["N"],82.08)
        self.assertEqual(F.transform_point([2,3],[8,10],[20,30],"MX"),[10,37])

    def test_corridor_goes_around_wall_and_prices_real_arc(self):
        boxes = [[40,20,60,80]]
        r = F.prepare_chain([10,50],[90,50],[100,100],boxes,2,reach=50,cell_clearance=.5,margin=2)
        self.assertTrue(r["fits"],r)
        self.assertGreaterEqual(r["length_um"],140)
        self.assertLess(r["length_um"],141)
        self.assertLessEqual(r["max_hop_um"],50)
        for leg in r["hop_paths_um"]:
            self.assertTrue(all(F.segment_clear(a,b,boxes) for a,b in zip(leg,leg[1:])))
        short = F.prepare_chain([10,50],[90,50],[100,100],boxes,1,reach=50,margin=2)
        self.assertFalse(short["fits"])
        self.assertEqual(short["minimum_stages"],2)
        self.assertEqual(short["stages"],1)

    def test_existing_fixed_cells_and_group_ownership_are_preserved(self):
        result = F.unowned_guides([
            {"name":"north","instances":["data0","addr0","we0"]},
            {"name":"east","instances":["we0","we1"]}],
            {"data0":{"status":"FIRM"},"addr0":{"status":"FIXED"}})
        self.assertEqual([g["instances"] for g in result["groups"]],[["we0"],["we1"]])
        self.assertEqual(len(result["excluded"]),3)

    def test_abutted_halves_have_no_parent_glue_capacity(self):
        p=dict(outline_um=[536.76,221.4],hard_cores=[
            dict(inst="w",origin_um=[0,0],outline_um=[268.38,221.4]),
            dict(inst="e",origin_um=[268.38,0],outline_um=[268.38,221.4])])
        r=F.parent_cell_space(p,glue_area_um2=.1)
        self.assertAlmostEqual(r["free_row_area_um2"],0)
        self.assertFalse(r["capacity_fits"])
        self.assertIsNone(F.parent_cell_space(p)["capacity_fits"])


if __name__ == "__main__":
    unittest.main()
