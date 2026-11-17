import json, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_preflight as KP


def kit(tmp, sites, band="533.0 667.14 537.3 671.46"):
    k = Path(tmp)
    (k / "landing_placement.tcl").write_text("set cland_groups {\n  {u_cland_raw_x_1 {%s} literal-local-reset}\n}\n" % ("{" in band and band or band))
    lines = ["set ff_bit_sites {}", "set ff_bit_site_cells {}", "dict set ff_bit_site_cells {ft0} {1.08 0.27}"]
    lines += ["dict set ff_bit_sites {ft0,1,%d} {%s %s}" % (i, x, y) for i, (x, y) in enumerate(sites)]
    (k / "ft_bit_sites.tcl").write_text("\n".join(lines) + "\n")
    return k


class ClandBandLegalSite(unittest.TestCase):
    def test_comb_of_ft_flops_leaves_no_legal_gap(self):
        with tempfile.TemporaryDirectory() as t:
            comb = [(533.0 + 2.16 * i, (2471 + r) * 0.27) for i in range(3) for r in range(15)]   # 1.08 dff every 2.16, all rows
            err = KP.cland_band_sites(kit(t, comb))
            self.assertEqual(len(err), 1)
            self.assertIn("no free gap", err[0])

    def test_free_row_or_strip_is_legal(self):
        with tempfile.TemporaryDirectory() as t:
            comb = [(533.0 + 2.16 * i, (2471 + r) * 0.27) for i in range(3) for r in range(1, 15)]   # row 0 left free
            self.assertEqual(KP.cland_band_sites(kit(t, comb)), [])
            self.assertEqual(KP.cland_band_sites(kit(t, [])), [])

    def test_missing_files_not_judged(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(KP.cland_band_sites(t), [])


if __name__ == "__main__":
    unittest.main()
