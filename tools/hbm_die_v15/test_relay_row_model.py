import unittest
from relay_row_model import layout, evaluate, Reservations, exact_contract_cost


class RowModel(unittest.TestCase):
    def test_exact_bit_mapping_orientations_reset_clock_and_escape(self):
        v = dict(w=64.8, h=23.76, pins={'a[0]': (0, 1), 'a[1]': (0, 20),
                                      'ck': (32, 0), 'rst_n': (63, 0)})
        v['directions'] = {p: 'OUTPUT' for p in v['pins']}
        sink = dict(v, directions={p: 'INPUT' for p in v['pins']})
        views = {'V': v, 'S': sink}; masters = {'we': 'V', 'ns': 'S'}
        pl = {'we': dict(x=0, y=0, orient='MY'), 'ns': dict(x=300, y=0, orient='R90')}
        widths = {(n, p): w for n in masters for p, w in [('a', 2), ('ck', 1), ('rst_n', 1)]}
        edges = [dict(source=['we', 'a', 0, 2], sink=['ns', 'a', 0, 2], bits=2),
                 dict(source=['we', 'ck', 0, 1], sink=['ns', 'ck', 0, 1], bits=1),
                 dict(source=['we', 'rst_n', 0, 1], sink=['ns', 'rst_n', 0, 1], bits=1)]
        r = exact_contract_cost(edges, pl, masters, views, widths)
        self.assertEqual(r['bits_checked'], 4)
        # Bit coordinates differ, clock/reset are included, no base-port centroid.
        self.assertTrue(r['feasible'])
        e = exact_contract_cost(edges, pl, masters, views, widths,
                                escape_um={('ns', 'a[1]'): 200})
        self.assertEqual(len(e['over_reach']), 1)
        del widths['ns', 'ck']
        with self.assertRaises(ValueError):
            exact_contract_cost(edges, pl, masters, views, widths)
        widths['ns', 'ck'] = 1
        sink['directions']['ck'] = 'OUTPUT'
        with self.assertRaises(ValueError):
            exact_contract_cost(edges, pl, masters, views, widths)

    def test_reservations_atomic_deterministic_and_oriented(self):
        views = {'V': dict(w=64.8, h=23.76)}
        masters = {'a': 'V', 'b': 'V'}
        p = {'b': dict(x=30, y=0, orient='R0'), 'a': dict(x=0, y=0, orient='R90')}
        r = Reservations((200, 200))
        self.assertEqual(r.reserve(p, views, masters), (True, None))
        self.assertEqual([x[0] for x in r.boxes], ['a', 'b'])
        before = list(r.boxes)
        self.assertFalse(r.reserve(p, views, masters)[0])
        self.assertEqual(r.boxes, before)

    def test_17_real_size_tiles_need_rank_geometry_not_shared_point(self):
        names = [f'l{i}' for i in range(17)]
        # Actual emitted NS624 LEF dimensions. Endpoint coupon intentionally
        # idealized, not asserted to be the current cij_SE physical placement.
        wh = (64.8, 23.76)
        pins = {(n, 'b'): (32.4, 23.76) for n in names}
        edges = [((n, 'b'), (194.4, 150.0)) for n in names]
        old = layout(names, wh, 17)
        folded = layout(names, wh, 6)
        self.assertAlmostEqual(old['width'], 1101.6)
        self.assertFalse(evaluate(old, (0, 0), pins, edges)['feasible'])
        self.assertTrue(evaluate(folded, (0, 0), pins, edges)['feasible'])
        self.assertEqual(set(folded['offsets']), set(names))
        self.assertAlmostEqual(folded['height'], 71.28)
        self.assertFalse(evaluate(folded, (0, 0), pins, edges,
                                 tile_wh=wh, reserved=[('hard', 0, 0, 10, 10)])['feasible'])

    def test_forwarded_clock_edge_and_missing_pin_are_not_hidden(self):
        row = layout(['a', 'b'], (64.8, 23.76), 1)
        pins = {('a', 'fwd'): (0, 0), ('b', 'clk'): (0, 0)}
        result = evaluate(row, (0, 0), pins, [(('a', 'fwd'), ('b', 'clk'))], reach=20)
        self.assertEqual(result['over_reach'], 1)
        with self.assertRaises(ValueError):
            evaluate(row, (0, 0), pins, [(('a', 'unknown'), (0, 0))])


if __name__ == '__main__':
    unittest.main()
