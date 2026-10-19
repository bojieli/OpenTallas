"""Use committed native command/configuration fixtures, without simulator or Git history."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'tools/hbm_static'), str(ROOT/'tools/hbm_layer_vehicle')]
import su_programme_compile as C
import native_su_calendar as N

PRODUCER = ROOT/'results/rtl/token_producer_fix_1019/producer'
CALENDAR = ROOT/'results/rtl/hbm_native_calendar_1019'
CLOSURE = ROOT/'results/rtl/hbm_token_calendar_closure_1019'


class NativeImages(unittest.TestCase):
    def test_all_four_native_configuration_images_match_archived_positives(self):
        with tempfile.TemporaryDirectory() as tmp:
            for case in json.loads((PRODUCER/'cases.json').read_text()):
                with self.subTest(case=case['case']):
                    src = PRODUCER/f"case{case['case']}"
                    out = Path(tmp)/str(case['case'])
                    model = C.lower_columns(src/'expected.mem', out, resident_edges=7111)
                    self.assertEqual((out/'config.mem').read_bytes(), (src/'config.mem').read_bytes())
                    self.assertEqual(model['edges'], case['commands'])
                    self.assertTrue(all(col['index_banks'] == 4 for col in model['columns']))

    def test_legacy_configuration_and_capacity_guard(self):
        with tempfile.TemporaryDirectory() as tmp:
            model = C.lower_columns(PRODUCER/'expected.mem', Path(tmp)/'legacy')
            self.assertEqual((Path(tmp)/'legacy/config.mem').read_bytes(), (PRODUCER/'config_old.mem').read_bytes())
            self.assertTrue(all(col['index_banks'] == 1 for col in model['columns']))
            with self.assertRaisesRegex(AssertionError, 'resident producer capacity'):
                C.lower_columns(PRODUCER/'expected.mem', Path(tmp)/'too_small', resident_edges=43)

    def test_release_calendar_matches_exact_native_run_and_refuses_bad_profiles(self):
        commands = [int(x,16) for x in (CALENDAR/'readback_expected.mem').read_text().split()]
        kw = dict(first_serial=2675, bridge_serial=2675, bridge_stream=3567, host_launch=3500, rows=160)
        words, model = N.compile_calendar(commands, **kw, request_lane_edges=4)
        actual = hashlib.sha256(''.join(f'{word:064x}\n' for word in words).encode()).hexdigest()
        hashes = {line.split()[1]:line.split()[0] for line in (CLOSURE/'release18_source.sha256').read_text().splitlines()}
        self.assertEqual(actual, hashes['calendar.mem'])
        self.assertFalse(model['qualified'])
        self.assertEqual(model['lg_to_vm_pin_edges'], 6)
        self.assertEqual(sum(e['kind']=='read' for e in model['events']), 32)
        self.assertEqual(sum(e['kind']=='write' for e in model['events']), 16)
        for depth in (-1, 1.5, 200):
            with self.subTest(depth=depth), self.assertRaises(ValueError):
                N.compile_calendar(commands, **kw, request_lane_edges=depth)
        # A wrong physical bank identity must never produce an accepted calendar.
        bad = list(commands)
        i = next(i for i,w in enumerate(bad) if (w >> (440+29)) & 1)
        bad[i] ^= 1 << (440+13)
        with self.assertRaisesRegex(ValueError, 'names sector'):
            N.compile_calendar(bad, **kw)


if __name__ == '__main__':
    unittest.main()
