import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
spec=importlib.util.spec_from_file_location('isolated_trigger',Path(__file__).with_name('trigger.py'))
T=importlib.util.module_from_spec(spec);spec.loader.exec_module(T)

class Isolation(unittest.TestCase):
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

if __name__=='__main__':unittest.main()
