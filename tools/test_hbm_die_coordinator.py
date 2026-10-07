"""Focused contracts for the coordinator's opt-in pin/receipt integration."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import hbm_die_views as V


class Coordinator(unittest.TestCase):
    def tearDown(self):
        V.L.VARIANT = ''
        V._MODEL.clear()

    def test_candidate_clock_lattice_and_station_identity(self):
        V.L.VARIANT = ''
        V._MODEL.clear()
        base = V.model()[0]
        station = lambda m: {(i.name, i.master, i.x, i.y) for i in m['insts'] if i.kind == 'waypoint'}
        self.assertFalse(base['variant'].get('vm_centre_ck', False))
        V.L.VARIANT = 'r19c'
        V._MODEL.clear()
        m, _, masters, _ = V.model()
        self.assertEqual(station(base), station(m))
        for i in m['insts']:
            if i.master in V.H.VM_CENTRE:
                ck = masters[i.master].ports['ck']
                self.assertEqual(ck[:2], ('area', 'M7'))
                self.assertEqual(round((i.x + ck[2]) * 1000) % 64, 16)
                self.assertEqual(round(i.x * 1000) % 54, 0)
                self.assertLess(abs(ck[2] - i.w / 2), 1)
        names = {i.master for i in m['insts']}
        self.assertNotIn('hfd_cmdproc', names)
        self.assertTrue({'hfd_cmdproc_n', 'hfd_cmdproc_s'} <= names)
        self.assertEqual(V.check_lef('hfd_cmdproc_n', V.ROOT / 'physical/hbm_accel_die_views/cmdproc/view_n/hfd_cmdproc_n.lef')['verdict'], 'MATCH')

    def test_receipts_do_not_grant_parent_credit(self):
        rows = V.receipt_views()
        self.assertIn('hfd_cmdproc_n', rows)
        for r in rows.values():
            self.assertFalse(r['functional_closure'])
            self.assertFalse(r['die_context_closed'])
            self.assertTrue(r['files_sha256'])

    def test_common_baseline_units(self):
        base, delta = 537.376, 22.17
        self.assertAlmostEqual(100 * delta / base, 4.125602, places=5)
        self.assertAlmostEqual(100 * delta / (base + delta), 3.962140, places=5)


if __name__ == '__main__':
    unittest.main()
