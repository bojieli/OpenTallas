import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from audit_registered_clocks import audit, clock_ports


class RegisteredClocks(unittest.TestCase):
    def test_forwarded_clock_is_not_data_even_with_a_different_primary_clock(self):
        sdc = '''create_clock -name w_fi0 -period 833.331 [get_ports {fi0[0]}]
create_clock -name core_clk -period 1111.108 [get_ports {ck[0]}]
create_clock -name virtual -period 1111.108
'''
        spec = dict(top='cross', clock_port='ck', sdc_extra=['cross.sdc'],
                    pin_regs=dict(enable=True, exclude='^(di0|rs)$'))
        env = 'EXTRA=(--orfs-var OT_PIN_REGS=1 --orfs-var OT_PIN_REGS_CLOCK=ck)'
        result = audit(spec, env, lambda _: sdc)
        self.assertEqual(result['planned_registered_clock_ports'], ['fi0'])
        spec['pin_regs']['exclude'] = '^(di0|fi0|rs)$'
        self.assertEqual(audit(spec, env, lambda _: sdc)['planned_registered_clock_ports'], [])

    def test_generated_clock_source_and_target_both_need_passthrough(self):
        ports, unknown = clock_ports('create_generated_clock -name out -source [get_ports ck] \\\n+  [get_ports -quiet {fo}]')
        self.assertEqual(ports, {'ck', 'fo'})
        self.assertFalse(unknown)

    def test_dynamic_or_missing_clock_constraints_are_unresolved(self):
        spec = dict(top='x', clock_port='ck', sdc_extra=['x'], pin_regs={})
        env = 'OT_PIN_REGS=1 OT_PIN_REGS_CLOCK=ck'
        for text in ('create_clock -period 100 [get_ports $clock]',
                     'create_clock -period 100 [get_ports {ck*}]', None):
            self.assertEqual(audit(spec, env, lambda _: text)['status'], 'UNRESOLVED')


if __name__ == '__main__':
    unittest.main()
