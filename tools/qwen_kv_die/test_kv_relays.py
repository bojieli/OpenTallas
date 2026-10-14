import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import kv_die as K
import kv_relays as R


class RealEndDirections(unittest.TestCase):
    def check_chain(self, text, rel=None):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            rtl = root / 'ends.sv'
            rtl.write_text("module src(output wire [3:0] data, input wire credit); endmodule\n"
                           "module dst(input wire [3:0] data, output wire credit); endmodule\n")
            die = root / 'die.v'
            die.write_text(text)
            bindings = {n: dict(file=str(rtl), module=n, ports={'p': ['data', 'credit']})
                        for n in ['src', 'dst']}
            default = {'qkd_rly_5': dict(w=5, fwd=set(range(4)), rev={4})}
            with patch.object(K, '_set_geometry'), patch.object(K, 'BINDINGS', bindings):
                return R.crosscheck(rel or default, die)

    def chain(self, last='  dst sink (.p(n2));\n', middle='qkd_rly_5'):
        return ('  src source (.p(n0));\n'
                '  qkd_rly_5 r0 (.a(n0), .b(n1), .ck(clk));\n'
                f'  {middle} r1 (.a(n1), .b(n2), .ck(clk));\n' + last)

    def test_data_and_reverse_credit_match_both_real_ends(self):
        self.assertEqual(self.check_chain(self.chain()), ([], 2))

    def test_wrong_real_endpoint_is_observed(self):
        conflicts, checked = self.check_chain(self.chain(last='  src sink (.p(n2));\n'))
        self.assertEqual(checked, 2)
        self.assertEqual({c[2] for c in conflicts}, set(range(5)))

    def test_open_tail_does_not_crash_or_invent_an_endpoint(self):
        self.assertEqual(self.check_chain(self.chain(last='')), ([], 1))

    def test_middle_stage_direction_change_is_rejected(self):
        rel = {'qkd_rly_5': dict(w=5, fwd=set(range(4)), rev={4}),
               'qkd_rly_bad': dict(w=5, fwd={0, 1, 2, 4}, rev={3})}
        with self.assertRaisesRegex(ValueError, 'direction changes'):
            self.check_chain(self.chain(middle='qkd_rly_bad'), rel)

    def test_cycle_has_no_unchecked_success(self):
        with self.assertRaisesRegex(ValueError, 'without an upstream head'):
            self.check_chain('  qkd_rly_5 r0 (.a(n0), .b(n1), .ck(clk));\n'
                             '  qkd_rly_5 r1 (.a(n1), .b(n0), .ck(clk));\n')

    def test_branch_is_explicitly_unqualified(self):
        with self.assertRaisesRegex(ValueError, 'branched relay net'):
            self.check_chain(self.chain(last='  dst s0 (.p(n2));\n  dst s1 (.p(n2));\n'))


if __name__ == '__main__':
    unittest.main()
