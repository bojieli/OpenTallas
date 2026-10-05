#!/usr/bin/env python3
"""Real tiny git histories exercise additive-only historical replay controls."""
import subprocess,tempfile,unittest
from pathlib import Path
import hbm_r6_archival_validation as A

class HistoricalControls(unittest.TestCase):
 def git(self,root,*args):return subprocess.check_output(['git',*args],cwd=root,stderr=subprocess.DEVNULL,text=True).strip()
 def fixture(self,root):
  self.git(root,'init','-q');self.git(root,'config','user.email','archive-test@example.invalid');self.git(root,'config','user.name','Archive Test')
  (root/'source').write_text('pinned');self.git(root,'add','source');self.git(root,'commit','-qm','original');return self.git(root,'rev-parse','HEAD')
 def addition(self,root):
  (root/'successor').write_text('additive');self.git(root,'add','successor');self.git(root,'commit','-qm','addition');return self.git(root,'rev-parse','HEAD')
 def test_exact_original(self):
  with tempfile.TemporaryDirectory()as d:
   root=Path(d);old=self.fixture(root);s=A.historical_worker_state(root,old);self.assertEqual(s['replay_mode'],'exact_admitted_HEAD')
 def test_clean_additive_descendant(self):
  with tempfile.TemporaryDirectory()as d:
   root=Path(d);old=self.fixture(root);new=self.addition(root);s=A.historical_worker_state(root,old,new)
   self.assertEqual(s['replay_mode'],'verified_additive_descendant');self.assertEqual(s['successor_added_paths'],1);self.assertEqual(s['historical_source_commit'],old)
 def test_changed_original_refused(self):
  with tempfile.TemporaryDirectory()as d:
   root=Path(d);old=self.fixture(root);(root/'source').write_text('changed');self.git(root,'add','source');self.git(root,'commit','-qm','changed')
   with self.assertRaisesRegex(ValueError,'historical tracked file'):A.historical_worker_state(root,old)
 def test_removed_original_refused(self):
  with tempfile.TemporaryDirectory()as d:
   root=Path(d);old=self.fixture(root);self.git(root,'rm','source');self.git(root,'commit','-qm','removed')
   with self.assertRaisesRegex(ValueError,'historical tracked file'):A.historical_worker_state(root,old)
 def test_dirty_worker_refused(self):
  with tempfile.TemporaryDirectory()as d:
   root=Path(d);old=self.fixture(root);(root/'untracked').write_text('dirty')
   with self.assertRaisesRegex(ValueError,'remain clean'):A.historical_worker_state(root,old)
 def test_unrelated_history_refused(self):
  with tempfile.TemporaryDirectory()as d:
   root=Path(d);old=self.fixture(root);self.git(root,'checkout','--orphan','other');self.git(root,'commit','-qm','unrelated')
   with self.assertRaisesRegex(ValueError,'not a descendant'):A.historical_worker_state(root,old)
 def test_head_changed_mid_replay_refused(self):
  with tempfile.TemporaryDirectory()as d:
   root=Path(d);old=self.fixture(root);self.addition(root)
   with self.assertRaisesRegex(ValueError,'changed during'):A.historical_worker_state(root,old,old)

if __name__=='__main__':unittest.main()
