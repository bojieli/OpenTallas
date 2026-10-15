"""dataflow_links.py: chains collapse through registers, bypass counts only unrelated blocks, pin-less ends clip to outlines."""
import unittest
import dataflow_links as D


class T(unittest.TestCase):
    def build(self):
        B = D.Builder()
        B.block('a', 'm', 'k', 'ga', 0, 0, 100, 100)
        B.block('r1', 'rly', 'rly', None, 400, 40, 10, 10, reg=True)
        B.block('b', 'm', 'k', 'gb', 800, 0, 100, 100)
        B.block('mid', 'm', 'k', 'gm', 200, 0, 100, 100)        # unrelated block under the a-b flight line
        B.block('a2', 'm', 'k', 'ga', 200, 200, 50, 50)         # same group as a: related, never a bypass
        return B

    def test_chain_and_crossing(self):
        B = self.build()
        pins = {('a', 'o'): (100, 50), ('r1', 'i'): (400, 45), ('r1', 'o'): (410, 45), ('b', 'i'): (800, 50)}
        data = [('d0', 'lane', 8, [('a', 'o'), ('r1', 'i')]), ('d1', 'lane', 8, [('r1', 'o'), ('b', 'i')])]
        D.collapse(B, data, {'r1'}, lambda n, p, bits: (pins.get((n, p)), 'pin'), True)
        blocks, links = B.finish()
        self.assertEqual(len(links), 1)
        l = links[0]
        self.assertEqual(l['s'], 1)                       # one register stage
        self.assertEqual(len(l['h']), 2)
        self.assertAlmostEqual(l['L'], 305 + 395, delta=1)  # driver -> sink along the hops (Manhattan)
        self.assertEqual(l['x'], 1)                        # crosses 'mid' only
        self.assertEqual(blocks['name'][l['xb'][0]], 'mid')

    def test_box_ends_clip_and_related_group(self):
        B = self.build()
        B.link('x', 'c', 4, [(0, None, None, None), (4, None, None, None)], False)
        blocks, links = B.finish()
        e = links[0]['e']
        self.assertEqual(e[0][4], 'box')
        self.assertTrue(0 <= e[0][2] <= 100 and 0 <= e[0][3] <= 100)   # on a's outline, not its centre
        self.assertEqual(links[0]['L'], 200)                            # corner to corner, a lower bound (centres: 350)
        self.assertEqual(links[0]['x'], 0)

    def test_metrics(self):
        m = D.metrics(dict(outline=[1000, 1000], reach_um=300, stages_explicit=False),
                      [dict(b=10, L=700, mh=700, s=None, bu=7000, e=[[0, None, 0, 10, 'pin'], [1, None, 700, 10, 'pin']])])
        self.assertEqual(m['over_reach_bits'], 10)
        self.assertEqual(m['needed_relay_bit_stages_lower_bound'], 20)
        self.assertGreater(m['worst_cut'], 0)


if __name__ == '__main__':
    unittest.main()
