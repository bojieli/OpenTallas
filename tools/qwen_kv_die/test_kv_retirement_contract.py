"""KV-RETIRE 10-19: contract builder unit tests (synthetic plane; no compile_all)."""
import json
import tempfile
import unittest
from pathlib import Path

import kv_retirement_contract as K
from kv_retirement import prove


def plane(td):
    succ = dict(sources=[dict(id='rly_a.fault', clock='c'), dict(id='existing_ufh', clock='c'),
                         dict(id='dcal.fault', clock='c')],
                leaf_latencies={'rly_a.fault': 180, 'existing_ufh': 105, 'dcal.fault': 2})
    rc = dict(source_clears=[dict(id='rly_a.fault', depth=19, downstream=178),
                             dict(id='existing_ufh', depth=15, downstream=103)])
    a, b = Path(td) / 's.json', Path(td) / 'r.json'
    a.write_text(json.dumps(succ)); b.write_text(json.dumps(rc))
    return a, b


PROG = dict(compiled_rx_cmd=2, compiled_tx_first=1752, compiled_end=1786, service_end=1779)


class Contract(unittest.TestCase):
    def test_cutoff_path_and_exact_status(self):
        with tempfile.TemporaryDirectory() as td:
            c = K.build(*plane(td), PROG, 11)
        cutoff, path, status = K.required_status(c, 1752)
        self.assertEqual(cutoff, 1752 + 33)                 # RESULT drain / done / slot missing checks
        self.assertEqual(path, 180 + 1 + 0 + 1 + 1 + 11 + 1)
        self.assertEqual(status, cutoff + path)
        r = prove(c, 1752, status)
        self.assertEqual(r['status'], 'LOGICAL_ONLY')       # no physical receipt can qualify
        with self.assertRaisesRegex(ValueError, 'precedes'):
            prove(c, 1752, status - 1)

    def test_every_source_has_an_operation_and_dcal_is_inventoried(self):
        with tempfile.TemporaryDirectory() as td:
            c = K.build(*plane(td), PROG, 11)
        self.assertIn('dcal.fault', c['source_inventory'])
        owned = set().union(*(o['fault_sources'] for o in c['operations']))
        self.assertEqual(owned, set(c['source_inventory']))
        ufh = [s for s in c['sources'] if s['id'] == 'existing_ufh'][0]
        self.assertEqual(ufh['path'][1]['edges'], K.AHUB_UFH_EDGES)

    def test_reset_release_covers_every_clear_plus_flush(self):
        with tempfile.TemporaryDirectory() as td:
            c = K.build(*plane(td), PROG, 11)
        need = c['reset']['required_sink_release_depth']
        self.assertEqual(need, 19 + 64 + 180)
        self.assertGreater(need, 255)                      # beyond the old 8-bit hold counter
        self.assertEqual(c['reset']['hold_counter_bits'], 9)
        c['sources'][0]['sink_release_age'] = 128          # HOLD128 is no proof
        with self.assertRaisesRegex(ValueError, 'resurrection'):
            prove(c, 1752, K.required_status(c, 1752)[2])

    def test_dcal_alternative_sink_prices_its_relay(self):
        with tempfile.TemporaryDirectory() as td:
            c = K.build(*plane(td), PROG, 11, dcal_sink=30)
        d = [s for s in c['sources'] if s['id'] == 'dcal.fault'][0]
        self.assertEqual(d['path'][0]['edges'], 31)

    def test_dropped_operation_deadline_refused(self):
        with tempfile.TemporaryDirectory() as td:
            c = K.build(*plane(td), PROG, 11)
        del c['operations'][-1]['missing_check']
        with self.assertRaises(KeyError):
            prove(c, 1752, 2000)


if __name__ == '__main__':
    unittest.main()
