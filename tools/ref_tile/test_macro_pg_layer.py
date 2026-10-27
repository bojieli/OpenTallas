"""Explicit PMA PG layers must not inherit the SRAM M4 grid."""
import unittest
import ref_tile as R

class MacroPG(unittest.TestCase):
    def test_mixed_pma_and_sram(self):
        spec = dict(name='mixed', kind='cluster', route={}, macros=[
            dict(view='p/ot_s81_pma_rxn', pg_layer='M5'),
            dict(view='p/ot_s81_pma_txm', pg_layer='M5'),
            dict(view='p/ot_sram')])
        t = R.gen_pdn(spec, dict(pg_layer='M7', children={}))
        self.assertIn('set ot_s [ot_ref_present {ot_s81_pma_rxn ot_s81_pma_txm}]', t)
        self.assertIn('add_pdn_connect -grid {macro_m5} -layers {M5 M6}', t)
        self.assertIn('set ot_s [ot_ref_present {ot_sram}]', t)
        self.assertIn('add_pdn_connect -grid {sram} -layers {M4 M5}', t)

    def test_conflicting_master_layer_refused(self):
        spec = dict(name='bad', kind='cluster', route={}, macros=[
            dict(view='p/pma', pg_layer='M5'), dict(view='p/pma')])
        with self.assertRaises(R.SpecError):
            R.gen_pdn(spec, dict(pg_layer='M7', children={}))

if __name__ == '__main__': unittest.main()
