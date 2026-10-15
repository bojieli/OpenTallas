#!/usr/bin/env python3
"""Synthetic production-shape calendar and mechanism-specific negative tests."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / 'tools/hbm_static/su_lifetime_calendar.py'
spec = importlib.util.spec_from_file_location('calendar_proof', SOURCE)
proof = importlib.util.module_from_spec(spec)
spec.loader.exec_module(proof)


def fixture():
    c = dict(N=512, M=128, allocations=[], writes=[], drains=[])
    # 128 real-sized 5120-word rows, rotating all four frames 32 times.
    # 32 sectors/cycle stages each row in20edges; native delayed commits
    # finish before the compute wave, and drain read/capture precede reuse.
    for index in range(128):
        start = index * 100
        a = dict(id=f'row{index}', owner=f'op{index}', frame=index % 4,
                 generation=index // 4, begin=start, end=start + 400,
                 sources=dict(stage=f'vm.row{index}', compute=f'su.row{index}'))
        c['allocations'].append(a)
        def ev(sector, edge, latency, mask, source):
            return dict(allocation=a['id'], owner=a['owner'], frame=a['frame'],
                        generation=a['generation'], sector=sector,
                        issue_edge=start + edge, latency=latency,
                        capture_edge=start + edge + latency, mask=mask, source=source)
        for sector in range(640):
            c['writes'].append(dict(ev(sector, sector // 32, 7, 255,
                                      a['sources']['stage']), kind='stage'))
            # 512-word waves =>64sectors/edge. Sparse output mask exercises
            # actual per-word drain masks rather than a blanket full row.
            mask = (0x55, 0xaa, 0xff, 0x01)[sector % 4]
            c['writes'].append(dict(ev(sector, 40 + sector // 64, 4, mask,
                                      a['sources']['compute']), kind='compute'))
            c['drains'].append(ev(sector, 60 + sector // 32, 7, mask,
                                  a['sources']['compute']))
    return c


class CalendarTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.calendar = fixture()

    def reject(self, mutate, message):
        c = copy.deepcopy(self.calendar)
        mutate(c)
        with self.assertRaisesRegex(proof.CalendarError, message):
            proof.validate(c)

    def test_production_shape(self):
        r = proof.validate(self.calendar)
        self.assertEqual((r['allocations'], r['frames_used'], r['frame_reuses']),
                         (128, 4, 124))
        self.assertEqual(r['drain_events'], 128 * 640)

    def test_stale_stage_capture_at_reuse(self):
        def mutate(c):
            w = c['writes'][0]
            w.update(issue_edge=399, latency=1, capture_edge=400)
        self.reject(mutate, 'outside ownership')

    def test_stale_compute_capture_after_reuse(self):
        def mutate(c):
            w = c['writes'][1]
            w.update(issue_edge=398, latency=4, capture_edge=402)
        self.reject(mutate, 'outside ownership')

    def test_mask(self):
        self.reject(lambda c: c['drains'][0].update(mask=0x54), 'mask mismatch')

    def test_frame(self):
        self.reject(lambda c: c['writes'][0].update(frame=1), 'frame identity')

    def test_generation(self):
        self.reject(lambda c: c['drains'][-1].update(generation=0), 'generation identity')

    def test_source(self):
        self.reject(lambda c: c['writes'][1].update(source='su.row4'), 'source identity')

    def test_allocation(self):
        self.reject(lambda c: c['writes'][0].update(allocation='row4'), 'owner identity')

    def test_capture_declaration(self):
        self.reject(lambda c: c['writes'][0].update(capture_edge=8), 'latency/capture')

    def test_preedge_read(self):
        def mutate(c):
            d = c['drains'][0]
            d.update(issue_edge=44, capture_edge=51)
        self.reject(mutate, 'mask mismatch')

    def test_stage_overwrites_compute(self):
        def mutate(c):
            w = c['writes'][0]
            w.update(issue_edge=49, capture_edge=56)
        self.reject(mutate, 'mask mismatch')

    def test_write_collision(self):
        def mutate(c):
            w = c['writes'][0]
            w.update(issue_edge=37, capture_edge=44)
        self.reject(mutate, 'same-edge write collision')

    def test_overlap(self):
        self.reject(lambda c: c['allocations'][0].update(end=401), 'overlapping frame')


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(CalendarTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        raise SystemExit(1)
    c = fixture()
    receipt = dict(proof.validate(c), synthetic_calendar=True,
                   row_words=5120, tests_run=result.testsRun,
                   mutants_rejected=result.testsRun - 1,
                   source_sha256={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                  for p in (SOURCE, Path(__file__).resolve())},
                   fixture_sha256=hashlib.sha256(json.dumps(c, sort_keys=True).encode()).hexdigest())
    Path(__file__).with_name('receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
