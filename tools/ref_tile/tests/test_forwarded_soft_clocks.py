"""Forwarded soft clocks: exact source ownership and real STA without regional CTS."""
import os
import tempfile
import unittest
from pathlib import Path
import test_landed_forwarded_clock as F

CE, K = F.CE, F.K


def soft_spec(root):
    s = F.fixture(root)
    s['forwarded_soft_clocks'] = [dict(port='xk[0]', domain='core', cells=['rs0', 'rs1'])]
    return s


class Spec(unittest.TestCase):
    def test_real_clock_and_exact_contract(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); s = soft_spec(root)
            clocks = CE.clocks(s, 833.333)
            self.assertIn('create_clock -name ot_forwarded_0 -period 833.333000000 [get_ports {xk[0]}]', clocks)
            text = CE.generate(K.load(root, s), root)
            self.assertIn('set ::ot_ce_fwd_soft [dict create {xk[0]} {clock ot_forwarded_0 domain core cells {{rs0} {rs1}}}]', text)
            self.assertIn('missing or wrong-source register', text)
            self.assertIn('set_propagated_clock [get_clocks ot_forwarded_*]', text)
            self.assertIn('ot_ce_forwarded_soft_visit $corner groups', text)
            self.assertNotIn('set_false_path', text)

    def test_default_bytes(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); s = F.fixture(root)
            before = CE.generate(K.load(root, s), root); clocks = CE.clocks(s, 833.333)
            s['forwarded_soft_clocks'] = []
            self.assertEqual(before, CE.generate(K.load(root, s), root))
            self.assertEqual(clocks, CE.clocks(s, 833.333))

    def test_refusals(self):
        with tempfile.TemporaryDirectory() as d:
            s = soft_spec(Path(d))
            cases = [None, {}, [dict(port='xk[*]', domain='core', cells=['rs0'])],
                     [dict(port='xk[0]', domain='other', cells=['rs0'])],
                     [dict(port='xk[0]', domain='core', cells=['rs0','rs0'])],
                     s['forwarded_soft_clocks'] * 2,
                     [dict(port='d', domain='core', cells=['rs0'])]]
            for value in cases:
                with self.subTest(value=value), self.assertRaises(ValueError):
                    CE.forwarded_soft_clocks(dict(s, forwarded_soft_clocks=value))


@unittest.skipUnless(os.environ.get('OT_FRRST_FLEET_TEST') == '1' and K.available(), 'fleet OpenROAD required')
class Actual(unittest.TestCase):
    def flow(self, mutant=''):
        original_fixture, original_rtl = F.fixture, F.RTL
        def fixture(root, fwd2=None):
            s = original_fixture(root, fwd2)
            for m in ('fwd', 'fwd2'):
                p = root / m / 'insertion.json'
                import json
                rec = json.loads(p.read_text())
                for c in CE.CORNERS: rec[c]['boundary'].update(min=10, mean=20, max=30)
                p.write_text(json.dumps(rec))
            s['forwarded_soft_clocks'] = [dict(port='xk[0]', domain='core', cells=['rs0','rs1'])]
            if mutant == 'wrong_source': s['forwarded_soft_clocks'][0]['port'] = 'xk[1]'
            if mutant == 'undeclared': s['forwarded_soft_clocks'][0]['cells'] = ['rs0']
            if mutant == 'missing': s['forwarded_soft_clocks'][0]['cells'].append('missing')
            return s
        try:
            F.fixture = fixture
            F.RTL = original_rtl.replace('endmodule', '''DFFHQNx1_ASAP7_75t_R rs0 (.CLK(xk[0]), .D(d), .QN(rq));
DFFHQNx1_ASAP7_75t_R rs1 (.CLK(xk[0]), .D(rq), .QN(rq1));
endmodule''')
            return F.ForwardedOpenroad().run_flow('pre_cts' if mutant == 'pre_cts' else '')
        finally:
            F.fixture, F.RTL = original_fixture, original_rtl

    def test_actual_clock_ownership_and_regional_cts(self):
        rc, out = self.flow()
        self.assertEqual(rc, 0, out[-9000:])
        self.assertIn('OT_FORWARDED_SOFT preserved xk[0]', out)
        self.assertIn('OT_LANDED FORWARDED_SOFT_SINK tt xk[0] rs0/CLK', out)
        self.assertIn('OT_MULTI_ROOT OWNERSHIP PASS roots=2', out)

    def test_causal_source_and_membership_failures(self):
        for mutant in ('wrong_source', 'undeclared', 'missing'):
            with self.subTest(mutant=mutant):
                rc, out = self.flow(mutant)
                self.assertNotEqual(rc, 0, out[-9000:])
                self.assertRegex(out, 'OT_FORWARDED_SOFT: (missing or wrong-source|undeclared)')

if __name__ == '__main__': unittest.main()
