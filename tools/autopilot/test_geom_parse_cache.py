"""Repeated queue queries share journal parsing without sharing mutable verdict state."""
import unittest
from unittest import mock

import loopgaps as L


class GeometryParseCacheTest(unittest.TestCase):
    text = ("2026-11-06 02:00 GEOM REQ [CACHE B1] slice_station__t12 slice_station__t13\n"
            "2026-11-06 02:01 REPLY [CACHE B1] slice_station__t12: PASS -> route\n")

    def setUp(self):
        L._geom_events_cached.cache_clear()

    def verdict(self, text):
        return L.geom_verdicts(text, 'CACHE B1', 'slice_station__t12', '')[0]

    def test_many_queue_queries_parse_identical_journal_once(self):
        with mock.patch.object(L, 'parse_ts', wraps=L.parse_ts) as parse:
            self.assertEqual(self.verdict(self.text), 'PASS')
            calls = parse.call_count
            for i in range(13, 43):
                L.geom_verdicts(self.text, 'CACHE B1', 'slice_station__t' + str(i), '')
            self.assertEqual(parse.call_count, calls)

    def test_same_size_inplace_edit_and_appended_amendment_invalidate(self):
        self.assertEqual(self.verdict(self.text), 'PASS')
        changed = self.text.replace(': PASS ->', ': FAIL ->')
        self.assertEqual(len(changed), len(self.text))
        self.assertEqual(self.verdict(changed), 'FAIL')
        changed += '2026-11-06 02:02 AMEND [CACHE B1] slice_station__t12: PASS-COND -> route\n'
        self.assertEqual(self.verdict(changed), 'PASS-COND')
        changed += '2026-11-06 02:03 AMEND [CACHE B1] slice_station__t12: FAIL; withdraw previous route clearance\n'
        self.assertEqual(self.verdict(changed), 'FAIL')

    def test_caller_list_mutation_cannot_change_cached_events(self):
        reqs, replies = L.geom_events(self.text)
        reqs.clear()
        replies.clear()
        self.assertEqual(self.verdict(self.text), 'PASS')
        reqs, replies = L.geom_events(self.text)
        self.assertEqual((len(reqs), len(replies)), (1, 1))

    def test_line_views_stay_separate_and_retention_is_bounded(self):
        text = self.text + '    slice_station__t13: FAIL\n'
        joined = L.geom_events(text)[1][0][-1]
        physical = L.geom_events(text, keep_lines=True)[1][0][-1]
        self.assertNotIn('\n', joined)
        self.assertIn('\n', physical)
        for i in range(5):
            L.geom_events(text + str(i))
        self.assertEqual(L._geom_events_cached.cache_info().maxsize, 2)
        self.assertLessEqual(L._geom_events_cached.cache_info().currsize, 2)


if __name__ == '__main__':
    unittest.main()
