import gzip
import json
import pathlib
import unittest
from explorer_dataflow import dataflow, model_connections


def geom():
    return dict(die='fixture', commit='abc', key='pinned', inst=dict(name=['a', 'b'],
                x=[0, 20], y=[0, 0], w=[10, 10], h=[10, 10]),
                bus_classes=['payload', 'clock'], buses=[[0, 32, [0, 1]]])


class DataflowTest(unittest.TestCase):
    def test_cached_bus_not_schedule(self):
        out = dataflow(geom())
        e = out['edges'][0]
        self.assertEqual(e['width_bits'], 32)
        self.assertEqual(e['from'], [5, 5])
        self.assertFalse(e['directed'])
        self.assertIsNone(e['required_bps'])
        self.assertNotIn('src_node', e)
        self.assertEqual(out['coverage']['token_mapping'], 'unavailable')

    def test_preserve_raw_ports_unknown_endpoint_and_bad_width(self):
        g = geom()
        g['dataflow_connections'] = model_connections({'buses': [('actual_id', 'payload', -5, [('a', 'D'), ('missing', 'Q')])]})
        out = dataflow(g)
        self.assertEqual(out['edges'][0]['endpoints'][0]['port'], 'D')
        self.assertIsNone(out['edges'][0]['width_bits'])
        self.assertEqual(out['coverage']['unresolved_endpoints'], 1)
        self.assertIsNone(out['edges'][0]['to'])

    def test_filter_dependency_control(self):
        g = geom()
        g['dataflow_connections'] = [dict(kind='dependency'), dict(kind='ported_bus', bus_class='clock')]
        self.assertEqual(dataflow(g)['edges'], [])

    def test_broadcast_not_fabricated(self):
        g = geom(); g['buses'] = [[0, 16, [0, -100]]]
        out = dataflow(g)
        self.assertEqual(len(out['edges'][0]['endpoints']), 1)
        self.assertEqual(out['coverage']['omitted_broadcast_endpoints'], 99)

    def test_share_safe(self):
        g = geom(); g['dataflow_connections'] = model_connections({'buses': [('secret', 'payload', 32, [('a', 'D'), ('b', 'Q')])]})
        serialized = json.dumps(dataflow(g, safe=True))
        for value in ['secret', 'abc', 'pinned', '"port": "D"', '"instance": "a"']:
            self.assertNotIn(value, serialized)

    def test_existing_three_designs(self):
        base = pathlib.Path.home() / '.local/state/fleet-viz/explorer/geom'
        found = 0
        for name in ['qwen_r21b', 's81_layer_r3', 'hbm_r25gph']:
            path = base / (name + '.json.gz')
            if not path.exists():
                continue
            found += 1
            with gzip.open(path, 'rt') as f:
                g = json.load(f)
            out = dataflow(g)
            self.assertGreater(out['coverage']['connections'], 100)
            self.assertEqual(out['provenance']['commit'], g['commit'])
            self.assertEqual(out['coverage']['known_bandwidth'], 0)
        if found == 0:
            self.skipTest('deployment caches not installed')


if __name__ == '__main__':
    unittest.main()
