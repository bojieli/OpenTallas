"""Small physical checks for the recovered region IR model."""
import unittest

import infra_pg as PG


class IRModel(unittest.TestCase):
    def test_grid_current_scales_linearly_and_density_reduces_drop(self):
        dense = [PG.grid_entry(layer, 8.64) for layer in ("M8", "M9")]
        sparse = [PG.grid_entry(layer, 17.28) for layer in ("M8", "M9")]
        drop = PG.cell_drop(dense, 0.58, 150)
        self.assertGreater(drop, 0)
        self.assertAlmostEqual(PG.cell_drop(dense, 1.16, 150), 2 * drop, places=10)
        self.assertGreater(PG.cell_drop(sparse, 0.58, 150), drop)
        self.assertEqual(PG.cell_drop(dense, 0, 150), 0)

    def test_each_phy_has_its_own_supply_bumps(self):
        _, bumps = PG._phy_lattice([10, 20, 310, 320], PG.phy_pg_pitch("serdes"))
        self.assertEqual({net for net, _, _ in bumps}, {"VDD", "VSS"})
        self.assertTrue(all(10 < x < 310 and 20 < y < 320 for _, x, y in bumps))


if __name__ == "__main__":
    unittest.main()
