#!/usr/bin/env python3
"""MU-DIE-S81/PO2 (10-19): dv_bind strict landing reset check -- the bind table's landing_reset_stages must equal the
reset landing of the landing VIEW actually bound (source kit spec.json at the view's closure-job source commit).
Both directions FAIL: a po2 view (kit reset_landing 2 stages) bound without the key, and the key set on an old view."""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / 's81_dv'))
import dv_bind as B  # noqa: E402

KIT = 'physical/ref_tile/s81dv_land_276'
M = 'dsfd_dvland_276'


def fake_repo(job, src, rl, with_verdict=True):
    """reader(ref, path) over a fake repo: record commit 'rec' holds the view (+ verdict), source commit src the kit"""
    files = {('rec', f'{KIT}/views/{M}/abstract.json'):
             json.dumps({'name': M, 'orfs_dir': f'/srv/x/claude/closure-loop/{job}/routes/a/work/orfs'})}
    if with_verdict:
        files[('rec', f'results/closure_loop/{job}/verdict.json')] = json.dumps({'source_commit': src + 'f' * 33})
    spec = {'name': 's81dv_land_276'}
    if rl is not None:
        spec['reset_landing'] = {'enable': rl > 0, 'stages': rl, 'clock': 'ck'}
    files[(src + 'f' * 33 if with_verdict else src, f'{KIT}/spec.json')] = json.dumps(spec)
    return lambda ref, path: files.get((ref, path))


def table(key=None, job=None):
    T = {'land_views': {M: {'ref': 'codex/closure-record-x', 'commit': 'rec', 'kit': KIT, **({'job': job} if job else {})}}}
    if key is not None:
        T['landing_reset_stages'] = {M: key}
    return T


class LandResetCheck(unittest.TestCase):
    def test_po2_view_with_key_passes(self):
        r = B.landing_reset_check(table(2), {M}, fake_repo('s81dv_land_276-po2-df5c2d585', 'df5c2d585', 2))
        self.assertEqual(r['verdict'], 'PASS')
        self.assertEqual(r['rows'][0]['rl'], 2)

    def test_po2_view_without_key_fails(self):
        r = B.landing_reset_check(table(None), {M}, fake_repo('s81dv_land_276-po2-df5c2d585', 'df5c2d585', 2))
        self.assertEqual(r['verdict'], 'FAIL')
        self.assertIn('table landing_reset_stages 0 != view', r['mismatch'][0])

    def test_key_on_old_view_fails(self):
        r = B.landing_reset_check(table(2), {M}, fake_repo('s81dv_land_276-l2-101b4b20c', '101b4b20c', None))
        self.assertEqual(r['verdict'], 'FAIL')
        self.assertIn('reset_landing 0', r['mismatch'][0])

    def test_old_view_without_key_passes(self):
        r = B.landing_reset_check(table(None), {M}, fake_repo('s81dv_land_276-l2-101b4b20c', '101b4b20c', None))
        self.assertEqual(r['verdict'], 'PASS')

    def test_disabled_landing_counts_zero(self):
        r = B.landing_reset_check(table(None), {M}, fake_repo('s81dv_land_276-x-101b4b20c', '101b4b20c', 0))
        self.assertEqual(r['verdict'], 'PASS')

    def test_source_from_job_name_without_verdict(self):
        r = B.landing_reset_check(table(2), {M}, fake_repo('s81dv_land_276-po2-df5c2d585', 'df5c2d585', 2, with_verdict=False))
        self.assertEqual(r['verdict'], 'PASS')
        self.assertEqual(r['rows'][0]['source'], 'df5c2d585')

    def test_missing_view_is_unresolved_fail(self):
        r = B.landing_reset_check(table(2), {M}, lambda ref, path: None)
        self.assertEqual(r['verdict'], 'FAIL')
        self.assertTrue(r['unresolved'])

    def test_table_job_disagrees_with_view(self):
        r = B.landing_reset_check(table(2, job='s81dv_land_276-po2-df5c2d585'), {M},
                                  fake_repo('s81dv_land_276-l2-101b4b20c', '101b4b20c', None))
        self.assertEqual(r['verdict'], 'FAIL')
        self.assertIn('table names job', r['unresolved'][0])

    def test_non_landing_masters_ignored_and_unused_keys_listed(self):
        T = table(2)
        T['landing_reset_stages']['dsfd_dvland_70'] = 2
        r = B.landing_reset_check(T, {M, 'dsdv_slice'}, fake_repo('s81dv_land_276-po2-df5c2d585', 'df5c2d585', 2))
        self.assertEqual(r['verdict'], 'PASS')
        self.assertEqual([x['master'] for x in r['rows']], [M])
        self.assertEqual(r['unused_keys'], ['dsfd_dvland_70'])


if __name__ == '__main__':
    unittest.main()
