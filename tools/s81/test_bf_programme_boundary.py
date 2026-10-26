import copy
import gzip
import json
import tempfile
import unittest
from pathlib import Path

import bf_programme_compile as compiler


class BoundaryTests(unittest.TestCase):
    def test_real_all_4288_issues_and_empty_phase(self):
        base = compiler.ROOT / 'results/rtl/s81_bf_programme_1015'
        with tempfile.TemporaryDirectory() as td:
            trace = Path(td) / 'trace.txt'
            trace.write_bytes(gzip.decompress((base / 'legacy_issue_trace.txt.gz').read_bytes()))
            phases = compiler.phases(trace)
        baseline = [int(x, 16) for x in (base / 'bf_desc.hex').read_text().splitlines()]
        count = 0
        for index, ph in enumerate(phases):
            fit = compiler.fit(ph)
            original, bad = (fit, []) if isinstance(fit, dict) else fit
            self.assertFalse(bad)
            self.assertEqual(compiler.pack(original), baseline[index])
            emitted = compiler.advance_descriptor(original)
            old_bits, new_bits = compiler.pack(original), compiler.pack(emitted)
            # Exact other 74 descriptor bits are preserved, including empty phases.
            self.assertEqual(old_bits & ~(255 << 15), new_bits & ~(255 << 15))
            if not original['n']:
                self.assertEqual(old_bits, new_bits)
            for i, expected in enumerate(ph['ev']):
                actual = compiler.word(emitted, i)
                actual['off'] += 1  # actual new front programme pin -> core extra edge
                self.assertEqual(actual, expected)
                # Deliberately unchanged OFF and double advance both miss the core edge.
                self.assertNotEqual(compiler.word(original, i)['off'] + 1, expected['off'])
                broken = copy.copy(emitted)
                broken['off'] -= 1
                self.assertNotEqual(compiler.word(broken, i)['off'] + 1, expected['off'])
                count += 1
        self.assertEqual((len(phases), count), (13, 4288))

    def test_reject_before_go_and_unproved_source(self):
        d = dict(n=1, off=1)
        with self.assertRaisesRegex(ValueError, 'first_e underflow'):
            compiler.advance_descriptor(d)
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / compiler.NLOCK_SOURCE
            p.parent.mkdir(parents=True)
            p.write_text('unproved new programme register')
            with self.assertRaisesRegex(ValueError, 'unmeasured'):
                compiler.boundary_descriptor(dict(n=1, off=8), 'c10_nlock', td)

    def test_empty_and_legacy_unchanged(self):
        self.assertEqual(compiler.advance_descriptor(dict(n=0, off=0)), dict(n=0, off=0))
        self.assertEqual(compiler.boundary_descriptor(dict(n=1, off=8)), dict(n=1, off=8))


if __name__ == '__main__':
    unittest.main()
