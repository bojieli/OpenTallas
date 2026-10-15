import base64
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

import export_lint_recovery as E


class ExportLintRecovery(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.run = Path(self.tmp.name)
        self.base = self.run / 'routes/L/work/orfs/results/asap7/block/base'
        self.base.mkdir(parents=True)
        for ext in ('odb', 'sdc', 'spef'):
            (self.base / ('6_final.' + ext)).write_text('retained original ' + ext)
        (self.run / 'cl').mkdir()
        (self.run / 'cl/child_lint.py').write_text('original frozen lint')
        (self.run / 'record').mkdir()
        (self.run / 'record/child_lint.json').write_text('{"verdict":"FAIL"}')
        self.j = dict(name='station', run=str(self.run), status='NEEDS_HUMAN', stage_key='collect',
                      commit_full='a' * 40, spec=dict(ref_tile=True), freeze_helper_overlay=True,
                      events=['route done (rc=0)', 'verdict -> CLOSED'],
                      crashes=[dict(tail='child_lint FAIL (b) pg: VDD: 0 full-length stripes')],
                      metrics=dict(drc=0, ss_ps=333.72, ff_ps=29.9, orfs_dir=str(self.base.parents[3])),
                      route_overlay_plan=dict(files=[dict(path='tools/hier_contract/child_lint.py',
                          sha256=E.digest(self.run / 'cl/child_lint.py'))]))
        (self.run / 'cl/helper_overlay_plan.json').write_text(json.dumps(self.j['route_overlay_plan']))
        data = b'new source-pinned lint'
        self.request = dict(job=self.j, helper_commit='b' * 40, helper_sha256=hashlib.sha256(data).hexdigest(),
                            helper_b64=base64.b64encode(data).decode())

    def test_preserves_originals_and_uses_only_explicit_lint(self):
        rec = E.prepare(self.request)
        self.assertEqual((self.run / 'cl/child_lint.py').read_text(), 'original frozen lint')
        d = Path(rec['directory'])
        self.assertEqual((d / 'original_record/child_lint.json').read_text(), '{"verdict":"FAIL"}')
        self.assertEqual(json.loads((d / 'original_job.json').read_text()), self.j)
        src = self.run / 'src'
        (src / 'tools/hier_contract').mkdir(parents=True)
        before, after = E.stage_script(rec, str(src))
        p = subprocess.run(['bash', '-c', before + after], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual((src / 'tools/hier_contract/child_lint.py').read_text(), 'new source-pinned lint')
        with self.assertRaises(FileExistsError):
            E.prepare(self.request)

    def test_guard_rejects_modified_physical_input_or_frozen_helper(self):
        rec = E.prepare(self.request)
        manifest = json.loads((Path(rec['directory']) / 'inputs.json').read_text())
        for path in (self.base / '6_final.odb', self.base / '6_final.sdc', self.base / '6_final.spef',
                     self.run / 'cl/child_lint.py', self.run / 'cl/helper_overlay_plan.json',
                     Path(rec['directory']) / 'child_lint.py'):
            old = path.read_bytes()
            path.write_bytes(old + b'changed')
            with self.assertRaisesRegex(ValueError, 'immutable input changed'):
                E.verify(manifest)
            path.write_bytes(old)
        E.verify(manifest)

    def test_guard_rejects_tampered_manifest_and_verifier_before_execution(self):
        rec = E.prepare(self.request)
        for name in ('inputs.json', 'verify.py'):
            path = Path(rec['directory']) / name
            old = path.read_bytes()
            path.write_bytes(old + b'changed')
            before, _ = E.stage_script(rec, str(self.run / 'src'))
            p = subprocess.run(['bash', '-c', before], capture_output=True, text=True)
            self.assertEqual(p.returncode, 91)
            path.write_bytes(old)

    def test_admission_refuses_non_collect_or_physical_failure_or_repeat(self):
        for patch in (dict(status='CLOSED'), dict(stage_key='route'), dict(freeze_helper_overlay=False),
                      dict(export_lint_recovery={'old': True}), dict(events=[]), dict(failed_checks=['drc']),
                      dict(metrics=dict(drc=1)), dict(metrics=dict(drc=0, ss_ps=-1, ff_ps=2)),
                      dict(crashes=[dict(tail='timing failed')])):
            with self.subTest(patch=patch), self.assertRaises(ValueError):
                E.eligible(dict(self.j, **patch))

    def test_missing_or_changed_inputs_refused_before_snapshot(self):
        (self.base / '6_final.spef').unlink()
        with self.assertRaisesRegex(ValueError, 'missing routed spef'):
            E.prepare(self.request)
        self.assertFalse((self.run / 'cl/export-lint-recovery').exists())


if __name__ == '__main__':
    unittest.main()
