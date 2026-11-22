import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
spec=importlib.util.spec_from_file_location('isolated_trigger',Path(__file__).with_name('trigger.py'))
T=importlib.util.module_from_spec(spec);spec.loader.exec_module(T)

class Isolation(unittest.TestCase):
    def test_uncollected_transient_does_not_expire_after_twelve_hours(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); run=root/"hbm_old";run.mkdir()
            (run/"canary_meta.json").write_text(json.dumps({"spec":{"die":"hbm"},"client_unit":"flow-canary-hbm-old"}))
            now=1000000;os.utime(run,(now-T.LIVE_S-3600,now-T.LIVE_S-3600))
            self.assertEqual(T.live_dies(root,now),{"hbm"})
            # A collected terminal verdict allows the next revision, regardless of age.
            (run/"canary.json").write_text("{}")
            self.assertEqual(T.live_dies(root,now),set())

    def test_legacy_metadata_keeps_age_fallback(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);run=root/"legacy";run.mkdir()
            (run/"canary_meta.json").write_text(json.dumps({"spec":{"die":"s81"}}))
            now=1000000;os.utime(run,(now-T.LIVE_S-1,now-T.LIVE_S-1))
            self.assertEqual(T.live_dies(root,now),set())
            os.utime(run,(now-10,now-10))
            self.assertEqual(T.live_dies(root,now),{"s81"})

    def test_slow_s81_does_not_hold_completed_dies(self):
        old=T.git
        try:
            T.git=lambda *a:SimpleNamespace(returncode=0,stdout='tools/die_plan/gen_phys.py\n')
            ready, revisions, hits=T.ready_dies('/src','new',['s81','hbm','qwen_compute'],['tools/die_plan/*'],
              {'last_sha':'old'}, {'s81'})
            self.assertEqual(ready,['hbm','qwen_compute'])
            self.assertNotIn('s81',revisions)
        finally:T.git=old
    def test_partial_submission_does_not_repeat_already_current_die(self):
        old=T.git
        try:
            T.git=lambda *a:SimpleNamespace(returncode=0,stdout='tools/die_plan/gen_phys.py\n')
            ready,_,_=T.ready_dies('/src','new',['s81','hbm'],['tools/die_plan/*'],
                {'last_sha':'old','die_sha':{'hbm':'new'}},set())
            self.assertEqual(ready,['s81'])
        finally:T.git=old
    def test_foreign_die_changes_trigger_only_own_reference(self):
        old=T.git
        try:
            T.git=lambda *a:SimpleNamespace(returncode=0,stdout='physical/die_plan/qwen_kvsys/cores/harden/gen_core_kit_kv.py\n')
            spec={'watch':['physical/die_plan/*'],
                  'die_plans':{'s81_head':['s81_head'], 'qwen_compute':['qwen_compute'],
                               'qwen_kvsys_core':['qwen_kvsys']}}
            ready,revisions,_=T.ready_dies('/src','new',list(spec['die_plans']),spec['watch'],
                {'last_sha':'old'},set(),spec=spec)
            self.assertEqual(ready,['qwen_kvsys_core'])
            self.assertEqual(revisions,{'s81_head':'new','qwen_compute':'new'})
        finally:T.git=old

    def test_snapshot_preserves_original_checkout_and_reuses_same_revision(self):
        with tempfile.TemporaryDirectory() as d:
            src=Path(d)/'src';src.mkdir()
            def g(*a):return subprocess.run(['git','-C',str(src),*a],check=True,capture_output=True,text=True)
            g('init','-q');g('config','user.name','Test');g('config','user.email','test@example.com')
            (src/'fixture').write_text('original')
            ref=src/'physical/ref_tile';(ref/'old_run').mkdir(parents=True)
            (ref/'required.json').write_text('{}');(ref/'old_run/routed.odb').write_text('historical')
            g('add','.');g('commit','-qm','first')
            sha=g('rev-parse','HEAD').stdout.strip()
            snap=T.source_snapshot(src,sha,Path(d)/'canary/runs')
            self.assertNotEqual(src,snap)
            self.assertTrue(T.source_lock_file(snap).exists())
            self.assertEqual((snap/'fixture').read_text(),'original')
            self.assertTrue((snap/'physical/ref_tile/required.json').exists())
            self.assertFalse((snap/'physical/ref_tile/old_run/routed.odb').exists())
            self.assertEqual(g('rev-parse','HEAD').stdout.strip(),sha)
            self.assertEqual(T.source_snapshot(src,sha,Path(d)/'canary/runs'),snap)
            runs=Path(d)/'canary/runs';r1=runs/'pending';r1.mkdir(parents=True)
            import json
            (r1/'canary_meta.json').write_text(json.dumps({'src':str(snap)}))
            self.assertEqual(T.unlock_completed_sources(src,runs),[])
            (r1/'canary.json').write_text('{}')
            self.assertEqual(T.unlock_completed_sources(src,runs),[str(snap)])
            self.assertFalse(T.source_lock_file(snap).exists())

def test_fresh_checkout_uses_normal_local_admission_on_source_volume(tmp_path, monkeypatch):
    root = tmp_path / "canary" / "runs"
    sources = root.parent / "sources"
    sources.mkdir(parents=True)
    sha = "123456789abcdef"
    calls = []

    def refuse(cmd, **kwargs):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 78, "", "disk floor refusal")

    monkeypatch.setattr(T.subprocess, "run", refuse)
    assert T.source_staging_refusal(root, sha) == "disk floor refusal"
    assert len(calls) == 1
    cmd = calls[0]
    assert cmd[cmd.index("--dir") + 1] == str(sources)
    assert cmd[cmd.index("--hosts") + 1] == "localhost"
    assert cmd[cmd.index("--disk") + 1] == str(T.SOURCE_STAGE_GB)
    assert {"--pick", "--strict-host"}.issubset(cmd)
    assert not T.snapshot_path(root, sha).exists()

    T.snapshot_path(root, sha).mkdir()
    assert T.source_staging_refusal(root, sha) == ""
    assert len(calls) == 1


if __name__=='__main__':unittest.main()
