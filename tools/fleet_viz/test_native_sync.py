"""native_sync.apply_receipts: which committed receipts override an own native-audit FAIL (NS-CASE 2026-10-18).

A relative-mode receipt PASS and a case-pin receipt PASS (native_pin_audit --case / the superseded --static-pins) stand
over an own-R FAIL of the same job / view; a plain receipt PASS does not; a receipt fills a job the own audit misses.
"""
import pathlib
import sys
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import native_sync as NS


def own(job, cell='qfd_landh_1_EW_65x30'):
    return dict(cell=cell, view='physical/ref_tile/x/views/' + cell, job=job, insertion=True, spread_ps=12.0,
                **{'pass': False, 'fail_why': 'capture 436.1 > 190 (3 pins)', 'capture_ps': 436.1, 'capture_pin': 'k0'})


def receipt(o, **kw):
    r = dict(cell=o['cell'], view=o['view'], job=o['job'], launch_ps=110.0, capture_ps=102.0, capture_pin='i[3]', fail_why='')
    r['pass'] = True
    r.update(kw)
    return r


class ApplyReceiptsTests(unittest.TestCase):
    def test_case_pin_receipt_overrides_own_fail(self):
        o = own('j-case')
        n = NS.apply_receipts([o], [(10, 'results/arch/l/native_q.json', receipt(o, case_pins=['k0', 'k1', 'k2']))])
        self.assertEqual(n, (0, 1))
        self.assertIs(o['pass'], True)
        self.assertEqual((o['capture_ps'], o['capture_pin'], o['case_pins']), (102.0, 'i[3]', ['k0', 'k1', 'k2']))
        self.assertEqual(o['own_fail_why'], 'capture 436.1 > 190 (3 pins)')
        self.assertEqual(o['receipt'], 'results/arch/l/native_q.json')

    def test_static_pin_receipt_overrides_own_fail(self):
        o = own('j-static')
        NS.apply_receipts([o], [(10, 'results/arch/s/native_s.json', receipt(o, static_pins={'k': 3}))])
        self.assertIs(o['pass'], True)
        self.assertEqual(o['static_pins'], {'k': 3})

    def test_relative_receipt_overrides_own_fail(self):
        o = own('j-rel')
        NS.apply_receipts([o], [(10, 'results/arch/r/native_r.json', receipt(o, relative_to='given 160'))])
        self.assertIs(o['pass'], True)

    def test_plain_or_empty_case_receipt_does_not_override(self):
        for kw in ({}, {'case_pins': []}, {'static_pins': {}}):
            o = own('j-plain')
            self.assertEqual(NS.apply_receipts([o], [(10, 'results/arch/p/native_p.json', receipt(o, **kw))]), (0, 0))
            self.assertIs(o['pass'], False)
            self.assertNotIn('receipt', o)

    def test_receipt_fail_never_overrides_and_newest_wins(self):
        o = own('j-new')
        old = receipt(o, case_pins=['k0'])
        new = receipt(o, case_pins=['k0'], **{'pass': False, 'fail_why': 'spread 90 > 80'})
        NS.apply_receipts([o], [(20, 'b.json', new), (10, 'a.json', old)])
        self.assertIs(o['pass'], False)

    def test_receipt_fills_uncovered_job(self):
        o = own('j-own')
        other = dict(own('j-other', cell='dsfd_dvland_70'))
        views = [o]
        self.assertEqual(NS.apply_receipts(views, [(10, 'f.json', receipt(other, case_pins=['k']))]), (1, 0))
        self.assertEqual(views[1]['src'], 'receipt f.json')


if __name__ == '__main__':
    unittest.main()
