import copy
import importlib.util
from pathlib import Path
import unittest
import json
import tempfile

from kv_retirement import prove


def fixture():
    roles = ['source_to_collector', 'ufh', 'afr', 'face', 'tx_capture',
             'tx_landing', 'link', 'consumer']
    return dict(operation_inventory=['token-op'], source_inventory=['landing'],
                edge_basis_qualified=False,
                operations=[dict(id='token-op', nominal_check=130, missing_check=132,
                                 drain=133, fault_sources=['landing'])],
                sources=[dict(id='landing', reset_clear_age=36,
                              reset_propagation_edges=180, sink_release_age=216,
                              reset_qualified=False,
                              path=[dict(role=role, edges=n, qualified=False,
                                         receipt_sha256='0'*64)
                                    for role, n in zip(roles, [180, 0, 1, 0, 1, 1, 13, 1])])])


class Retirement(unittest.TestCase):
    def test_complete_logical_fixture_remains_unqualified(self):
        r = prove(fixture(), 100, 330)
        self.assertFalse(r['qualified'])
        self.assertEqual(r['cutoff'], 133)
        self.assertEqual(r['sources'][0]['last_functional_observation'], 330)
        self.assertEqual(r['compiled_end'], 331)
        self.assertEqual(r['token_added_edges'], 36*197)

    def test_early_status_fails_at_exact_boundary(self):
        with self.assertRaisesRegex(ValueError, 'precedes'):
            prove(fixture(), 100, 329)

    def test_abstract_tree_receipt_never_qualifies_suffix(self):
        c = fixture()
        c['edge_basis_qualified'] = True
        c['sources'][0]['path'][0]['qualified'] = True
        self.assertFalse(prove(c, 100, 330)['qualified'])

    def test_missing_or_reordered_path_fails(self):
        for alter in ('drop', 'swap', 'receipt'):
            c = fixture()
            p = c['sources'][0]['path']
            if alter == 'drop': p.pop()
            elif alter == 'swap': p[0], p[1] = p[1], p[0]
            else: p[-1].pop('receipt_sha256')
            with self.subTest(alter=alter), self.assertRaises(ValueError):
                prove(c, 100, 330)

    def test_missing_deadline_and_uninventoried_source_fail(self):
        c = fixture()
        del c['operations'][0]['missing_check']
        with self.assertRaises(KeyError): prove(c, 100, 330)
        c = fixture()
        c['source_inventory'].append('kc')
        with self.assertRaisesRegex(ValueError, 'inventory'): prove(c, 100, 330)

    def test_reset_hold128_cannot_flush216_edge_path(self):
        c = fixture()
        c['sources'][0]['sink_release_age'] = 128
        with self.assertRaisesRegex(ValueError, 'resurrection'): prove(c, 100, 330)

    def test_overflow_and_boolean_ages_fail(self):
        with self.assertRaises(ValueError): prove(fixture(), 100, 65535)
        c = fixture()
        c['operations'][0]['drain'] = True
        with self.assertRaises(ValueError): prove(c, 100, 330)


class Calendar(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = Path(__file__).resolve().parents[1] / 'qwen_split/d2d_link_calendar.py'
        spec = importlib.util.spec_from_file_location('retirement_link', path)
        cls.link = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.link)

    def test_tail_moves_only_status_and_prices_window(self):
        a, wa = self.link.layer_msgs(0, 0, [20, 40, 20, 500], 6, 5)
        b, wb = self.link.layer_msgs(0, 0, [20, 40, 20, 500], 6, 5, status_delay=197)
        self.assertEqual(a[:-1], b[:-1])
        self.assertEqual(b[-1]['cyc'] - a[-1]['cyc'], 197)
        self.assertEqual(wb['attn_end'] - wa['attn_end'], 197)
        with self.assertRaises(ValueError):
            self.link.layer_msgs(0, 0, [20, 40, 20, 500], 6, 5, status_delay=-1)

    def test_every_layer_start_and_token_period_include_tail(self):
        groups = [dict(kind='layer', id=f'L{i}', start=100+i*1000, cycles=1000)
                  for i in range(36)]
        nodes = [dict(id='embed', cycles=100)]
        for g in groups:
            nodes += [dict(id=g['id']+'.'+op, cycles=n)
                      for op, n in zip(('rmsnorm1', 'qkv', 'qknorm_rope', 'attn_kv'),
                                       (20, 40, 20, 500))]
        with tempfile.NamedTemporaryFile(mode='w') as f:
            json.dump(dict(nodes=nodes, groups=groups, totals=dict(cycles=36100)), f)
            f.flush()
            a, x = self.link.program_profile(6, 5, f.name)
            b, y = self.link.program_profile(6, 5, f.name, status_delay=197)
        self.assertEqual(y['token_period']-x['token_period'], 36*197)
        for i, (old, new) in enumerate(zip(x['layers'], y['layers'])):
            self.assertEqual(new['start']-old['start'], i*197)
            self.assertEqual(new['cycles']-old['cycles'], 197)
        self.assertEqual([m for m in a if m['kind'] != 4],
                         [m for m in b if m['kind'] != 4])


if __name__ == '__main__':
    unittest.main()
