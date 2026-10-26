import tempfile
import unittest
from pathlib import Path
import die_sta as D


class RealViews(unittest.TestCase):
    def test_actual_files_and_all_corners_are_required(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'real.lib'
            p.write_text('library(test) { cell(tile) {} }')
            views = {c: {'tile': (p, 'closed')} for c in ('ss', 'tt', 'ff')}
            self.assertEqual(D.real_view_gate(['tile'], views)['verdict'], 'PASS')
            # An existing SS file must never silently satisfy a missing TT export.
            del views['tt']['tile']
            g = D.real_view_gate(['tile'], views)
            self.assertEqual(g['missing'], {'tile': {'tt': 'missing_real_corner_view'}})
            self.assertFalse(g['tt_fallback_to_ss'])
            views['tt']['tile'] = (p, 'interim')
            self.assertEqual(D.real_view_gate(['tile'], views)['verdict'], 'FAIL')
            views['tt']['tile'] = (p.with_name('absent.lib'), 'closed')
            self.assertEqual(D.real_view_gate(['tile'], views)['missing']['tile']['tt'], 'missing_library_file')

    def test_missing_masters_remain_distinct(self):
        g = D.real_view_gate(['lane_84', 'lane_86'], {})
        self.assertEqual(set(g['missing']), {'lane_84', 'lane_86'})
        self.assertEqual(g['required_masters'], 2)
        self.assertEqual(g['verdict'], 'FAIL')


if __name__ == '__main__':
    unittest.main()
