"""Conservative standard-cell placement classification, independent of path/count."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import macro_grid_lint as M
from test_hier_contract import FakeGit, SRAM, PLACE, place_spec


SAFE = '''if {[[$cell getMaster] isBlock]} {error {standard cells only}}
$cell setLocation 100 200
'''


class StandardCellClassification(unittest.TestCase):
    def test_direct_runtime_guard_proves_only_same_receiver(self):
        self.assertFalse(M.has_macro_move(SAFE))
        self.assertFalse(M.has_macro_move(SAFE.replace('setLocation', 'setOrigin')))
        self.assertTrue(M.has_macro_move(SAFE.replace('$cell setLocation', '$other setLocation')))

    def test_guard_cannot_hide_another_move_on_same_line(self):
        self.assertTrue(M.has_macro_move(SAFE.rstrip() + '; $macro setLocation 1 2\n'))
        self.assertTrue(M.has_macro_move(SAFE + 'place_macro -macro_name u -location {1 2}\n'))

    def test_nonfatal_guard_or_reassignment_is_not_proof(self):
        for changed in (SAFE.replace('error', 'puts'),
                        SAFE.replace('$cell setLocation', 'set cell $macro\n$cell setLocation'),
                        SAFE.replace('isBlock]', 'isBlock] == 0'),
                        SAFE.replace('{standard cells only}', '"bad [set cell $macro]"')):
            with self.subTest(changed=changed):
                self.assertTrue(M.has_macro_move(changed))

    def test_comments_cannot_establish_runtime_guard(self):
        self.assertTrue(M.has_macro_move('# ' + SAFE))
        self.assertTrue(M.has_macro_move('# continued comment \\\n' + SAFE))

    def test_no_lef_proven_cells_skip_but_unknown_move_stays_warn(self):
        spec = place_spec('cells.tcl')
        spec['stages']['route']['cmd'] = ('run --step-tcl pre_global_place=/src/physical/x/cells.tcl')
        result = M.check(spec, FakeGit({'physical/x/cells.tcl': SAFE}))
        self.assertEqual(result['verdict'], 'SKIP', result)
        result = M.check(spec, FakeGit({'physical/x/cells.tcl': '$macro setLocation 1 2\n'}))
        self.assertEqual(result['verdict'], 'WARN', result)
        self.assertIn('no macro LEF', result['message'])

    def test_real_offgrid_macro_remains_refused_alongside_guarded_cells(self):
        # Guarded code is an uncalled helper, as in the actual row-packing hook.
        text = 'proc pack {cell} {\n' + SAFE + '}\n' + PLACE % '0.010'
        git = FakeGit({'physical/x/route.sh': 'echo route',
                       'physical/m/ot_sram_t/ot_sram_t.lef': SRAM,
                       'physical/x/p.tcl': text})
        result = M.check(place_spec('p.tcl'), git)
        self.assertEqual(result['verdict'], 'REFUSE', result)
        self.assertIn('ot_sram_t at (20.000, 28.810)', result['message'])


if __name__ == '__main__':
    unittest.main()
