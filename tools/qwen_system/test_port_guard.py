"""Q7 negative gates: functional omissions must not become clean die views."""
import unittest
from types import SimpleNamespace

from qwen_system.port_guard import audit_dropped_ports


class PortGuard(unittest.TestCase):
    def setUp(self):
        self.masters = {'qfd_ctrl': SimpleNamespace(order=['clk', 'request', 'debug'],
            ports={'clk': ('area', 1), 'request': ('face', 624), 'debug': ('face', 8)})}
        self.exempt = {'qfd_ctrl.debug': {'class': 'debug', 'reason': 'Owner excludes DFT'}}

    def test_legacy_omissions_are_recorded(self):
        rows = audit_dropped_ports(self.masters, {'qfd_ctrl': {'clk'}})
        self.assertEqual([(r['port'], r['bits']) for r in rows], [('debug', 8), ('request', 624)])
        self.assertEqual(self.masters['qfd_ctrl'].order, ['clk', 'request', 'debug'])

    def test_strict_functional_omission_fails_before_deletion(self):
        with self.assertRaisesRegex(ValueError, 'qfd_ctrl.request'):
            audit_dropped_ports(self.masters, {'qfd_ctrl': {'clk'}}, strict=True,
                                bound_masters=['qfd_ctrl'], exemptions=self.exempt)

    def test_real_binding_and_classified_debug_pass(self):
        rows = audit_dropped_ports(self.masters, {'qfd_ctrl': {'clk', 'request'}}, strict=True,
                                  bound_masters=['qfd_ctrl'], exemptions=self.exempt)
        self.assertEqual(rows[0]['disposition'], 'debug')
        self.assertTrue(rows[0]['rtl_bound'])

    def test_missing_binding_inventory_fails(self):
        with self.assertRaisesRegex(ValueError, 'rtl_bound_masters'):
            audit_dropped_ports(self.masters, {}, strict=True)

    def test_unreasoned_exemption_fails(self):
        with self.assertRaisesRegex(ValueError, 'class and reason'):
            audit_dropped_ports(self.masters, {}, exemptions={'qfd_ctrl.request': {'class': 'by_design'}})


if __name__ == '__main__':
    unittest.main()
