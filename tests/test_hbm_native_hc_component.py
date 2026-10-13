"""The native HC helper is source-derived, honest about its status, and loads in the die compiler."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import hbm_native_integration_1013 as die  # noqa: E402

HC = 'results/arch/hbm_native_1013/hc/component.json'


class NativeHcComponent(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rec = json.loads((ROOT / HC).read_text())

    def test_regenerates_byte_identical(self):
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run([sys.executable, str(ROOT / 'tools/hbm_native_hc_component.py'), '--out', tmp],
                           check=True, capture_output=True)
            self.assertEqual((Path(tmp) / 'component.json').read_bytes(), (ROOT / HC).read_bytes())

    def test_two_die_placed_tiles_no_hard_parent(self):
        r = self.rec
        self.assertEqual(r['schema'], 'opentallas.hbm.native_component.v1')
        self.assertEqual([c['logical_module'] for c in r['children']], ['ot_hgi_hc_tile'] * 2)
        self.assertEqual([c['xy_um'] for c in r['children']], [[10.8, 15.12], [689.04, 15.12]])
        self.assertEqual({(c['w_um'], c['h_um']) for c in r['children']}, {(656.64, 725.76)})
        self.assertEqual(r['outline_um'], [1356.48, 756.0])
        self.assertFalse(r['hard_parent_created'])
        self.assertFalse(r['hierarchy']['third_hard_level'])
        self.assertEqual(len(r['replicated_instances']) * len(r['children']), 8)
        self.assertEqual(round(2 * 656.64 + 21.6 + 2 * 10.8, 6), 1356.48)
        self.assertEqual(round(725.76 + 2 * 15.12, 6), 756.0)

    def test_not_qualified(self):
        r = self.rec
        self.assertFalse(r['closed'])
        self.assertFalse(r['final_signoff_eligible'])
        self.assertEqual(r['status'], 'CANDIDATE_NOT_QUALIFIED')
        self.assertFalse(r['legacy_envelope']['functional_coverage'])
        for c in r['children']:
            self.assertIsNone(c['view_lef'])
            self.assertTrue(c['closure_status'].startswith('OPEN'))
        self.assertEqual([r['qualification'][k] for k in ('tile_tt', 'tile_ff', 'tile_drc')], [None] * 3)

    def test_interface(self):
        s = self.rec['interface_summary']
        self.assertEqual([s[k] for k in ('chain_in_bits', 'chain_out_bits', 'chain_mid_seam_bits', 'x_lanes', 'x_forward_bits',
                                         'x_return_bits', 'hbm_lanes')], [1065, 1065, 1065, 8, 1200, 16, 8])
        self.assertLess(self.rec['cut_ledger'][0]['ratio'], 0.55)

    def test_die_compiler_accepts(self):
        """Run the die compiler's own component validation, then place HC with its own helpers."""
        saved = dict(die.COMPONENTS)
        try:
            die.COMPONENTS['hc'] = HC
            with tempfile.TemporaryDirectory() as tmp:
                die.compose(Path(tmp))          # validates every COMPONENTS entry, HC included
                cand = json.loads((Path(tmp) / 'candidate.json').read_text())
        finally:
            die.COMPONENTS.clear(); die.COMPONENTS.update(saved)
        r, rows = self.rec, []
        self.assertEqual(die.outline(r), (1356.48, 756.0))
        reserved = {u['instance']: u for u in cand['unresolved_regions']}
        for q in r['die_quarter_placement']['instances']:
            res = reserved[q['replaces_reservation']]
            self.assertEqual((q['xy_um'], res['w_um'], res['h_um']), ([round(v, 6) for v in res['xy_um']], *die.outline(r)))
            for child in r['children']:
                raw = [q['xy_um'][i] + child['xy_um'][i] for i in (0, 1)]
                xy = [round(round(v / g) * g, 6) for v, g in zip(raw, die.GRID)]
                self.assertEqual(xy, [round(v, 6) for v in raw], 'HC child needs a grid correction')
                rows.append(dict(instance=die.physical_name(q['instance'] + '/' + child['instance']), xy_um=xy,
                                 w_um=child['w_um'], h_um=child['h_um']))
        self.assertEqual(len({x['instance'] for x in rows} | {c['instance'] for c in cand['children']}),
                         len(rows) + len(cand['children']))
        self.assertEqual(die.overlaps(cand['children'] + rows), die.overlaps(cand['children']))
        self.assertTrue(all(die.rect(x)[2] <= die.DIE[0] and die.rect(x)[3] <= die.DIE[1] for x in rows))
        print(f'HC_NATIVE_HELPER_ACCEPTED children={len(rows)} die_children={len(cand["children"])} new_overlaps=0 grid_corrections=0')


if __name__ == '__main__':
    unittest.main()
