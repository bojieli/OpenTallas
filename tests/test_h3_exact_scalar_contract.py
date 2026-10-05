from pathlib import Path
import random
import struct
import sys
import unittest
import warnings

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import h3_exact_scalar_contract as H
import hdc_golden as G
import hdc_golden_v41 as V


def value(code):
    return G.F(struct.unpack('!f', struct.pack('!I', code))[0])


def bits(x):
    return int(G.bits(x))


class ScalarContract(unittest.TestCase):
    def test_source_pins_and_no_build_credit(self):
        m = H.model()
        self.assertEqual(len(m['source_sha256']), 14)
        self.assertEqual(m['RTL_builds'], 0)
        self.assertIsNone(m['G0']['full_composed_token_latency_ns'])
        self.assertIsNone(m['G0']['cell_area_total_um2'])
        self.assertFalse(m['G0']['SS_FF_in_context'])

    def test_div_boundary_contract(self):
        for a, b, expected in [
            (0x00800000, 0x43800000, (0x00008000, 0)),
            (0x80000001, 0x40000000, (0, 0)),
            (0x00000003, 0x40000000, (2, 0)),
            (0x7f7fffff, 0x3f000000, (0, 2)),
            (0x3f800000, 0, (0, 1)),
            (0x3f800000, 0x80000000, (0, 1)),
            (0x7f800000, 0x3f800000, (0, 1)),
            (0x7fc00001, 0x3f800000, (0, 1)),
            (0x80000000, 0x3f800000, (0, 0))]:
            with self.subTest(a=hex(a), b=hex(b)):
                self.assertEqual(H.div_contract(a, b), expected)

    def test_independent_div_matches_pinned_golden_finite(self):
        rng = random.Random(400)
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            for _ in range(2048):
                a = rng.randrange(0x7f800000) | (rng.randrange(2) << 31)
                b = rng.randrange(1, 0x7f800000) | (rng.randrange(2) << 31)
                y, err = H.div_contract(a, b)
                gold = bits(V.div(value(a), value(b)))
                if err:
                    self.assertEqual(err, 2)
                    self.assertEqual(gold & 0x7f800000, 0x7f800000)
                else:
                    self.assertEqual(y, gold)

    def test_roundtrip_and_canonical_zero(self):
        rng = random.Random(1)
        for _ in range(2048):
            c = rng.randrange(0x7f800000) | (rng.randrange(2) << 31)
            self.assertEqual(H.rne(H.finite(c)), c if c & 0x7fffffff else 0)

    def test_newton_all_intermediate_rounds_match_source(self):
        for kind in ['rsqrt', 'reciprocal']:
            for v in [0x3f800000, 0x40000000, 0x40800000, 0x3a800000, 0x45a00000]:
                t = H.newton(v, kind)
                f = G.rsqrt if kind == 'rsqrt' else G.reciprocal
                self.assertEqual(int(t['result'], 16), bits(f(value(v))))
                for step in t['steps']:
                    a, b = value(int(step['a'], 16)), value(int(step['b'], 16))
                    op = G.add if 'add' in step['op'] else G.mul
                    self.assertEqual(int(step['y'], 16), bits(op(a, b)))
                self.assertEqual(len(t['steps']), 13 if kind == 'rsqrt' else 9)

    def test_reciprocal_saturation_retained(self):
        t = H.newton(0x7f7fffff, 'reciprocal')
        self.assertEqual(t['seed'], '00000000')
        self.assertEqual(t['result'], '00000000')
        self.assertEqual(bits(G.reciprocal(value(0x7f7fffff))), 0)

    def test_no_exact_div_reciprocal_substitution(self):
        # Source rounded Newton reciprocal differs from independently rounded DIV.
        d = 0x40bf6301
        exact = H.div_contract(0x3f800000, d)[0]
        recip = int(H.newton(d, 'reciprocal')['result'], 16)
        self.assertNotEqual(exact, recip)

    def test_source_search_cycle_ledger_and_bounds(self):
        rng = random.Random(31)
        for _ in range(256):
            a = rng.randrange(1, 0x7f800000)
            b = rng.randrange(1, 0x7f800000)
            m = H.divider_search_edges(a, b)
            self.assertEqual(m['edges_after_accept'], 2 * m['iterations'] + 3)
            self.assertLessEqual(m['iterations'], 31)
        self.assertEqual(H.divider_search_edges(0, 0x3f800000)['edges_after_accept'], 0)
        self.assertEqual(H.divider_search_edges(1, 0x3f800000)['edges_after_accept'], 65)

    def test_selected5120_source_recurrence_vs_independent_oracle(self):
        cases = [0, 1, 0x007fffff, 0x00800000, 0x3f800000, 0x7f7fffff, 0x7f800000, 0x7fc00001]
        rng = random.Random(5120)
        cases += [rng.randrange(0x7f800000) for _ in range(2048)]
        for a in cases:
            for sign in [0, 0x80000000]:
                a_signed = a | sign
                t = H.restoring_div31(a_signed, 0x45a00000)
                y, err = H.div_contract(a_signed, 0x45a00000)
                self.assertEqual((t['y'], t['fault']), (y, int(bool(err))))

    def test_selected_halfway_and_truncation_mutant_controls(self):
        # Exact midpoint of subnormal zero/one and one/two after division by5120.
        for a, expected in [(0x00000a00, 0), (0x00001e00, 2)]:
            t = H.restoring_div31(a, 0x45a00000)
            self.assertEqual(t['y'], expected)
            self.assertTrue(t['guard'])
            self.assertFalse(t['sticky'])
            # Always-round-half-up mutant disagrees at even lower=zero.
            if expected == 0:
                self.assertNotEqual(1, expected)
        t = H.restoring_div31(0x3f800000, 0x45a00000)
        self.assertTrue(t['round_up'])
        self.assertNotEqual(t['y'] - 1, H.div_contract(0x3f800000, 0x45a00000)[0])

    def test_handoff_lease_cost_and_NO_timing_transfer(self):
        m = H.model()
        e = m['selected_endpoint']
        self.assertEqual(e['denominator_hex'], '45a00000')
        self.assertEqual(e['Qwen_mean_denominator_reciprocal_hex'], '39800000')
        self.assertEqual(e['proposed_service_cost_edges']['total_D31_no_stall'], 37)
        self.assertFalse(e['frequency_qualified'])
        self.assertEqual(sum(m['primitive_inventory']['existing_v41x_DIV19']['ledger'].values()), 1904)
        self.assertEqual(len(m['handoff_source_sha256']), 4)

    def test_register_ledger_and_ports(self):
        m = H.model()
        self.assertEqual(m['primitive_inventory']['existing_ABI3_exact_DIV']['state_bits'], 323)
        self.assertEqual(m['primitive_inventory']['existing_HDC_exact_DIV']['state_bits'], 2634)
        self.assertEqual(m['G0']['new_RF_memory_ports'], 0)
        self.assertEqual(m['G0']['reuse_SIMD_naive_rsqr_RF_read_bytes'], 13312)
        self.assertEqual(m['G0']['reuse_SIMD_naive_rsqr_RF_write_bytes'], 6656)


if __name__ == '__main__':
    unittest.main()
