#!/usr/bin/env python3
"""Fail-closed archival identity controls; no production root edits."""
import json,unittest
from pathlib import Path
from unittest.mock import patch
import hbm_r9_archival_validation as A

class ArchivalControls(unittest.TestCase):
 def test_wrong_frozen_commit_refused(self):
  with patch.object(A.subprocess,'check_output',return_value='wrong\n'):
   with self.assertRaisesRegex(ValueError,'frozen source commit'):A.worker_state(Path('/unused'))
 def test_dirty_worker_refused(self):
  with patch.object(A.subprocess,'check_output',side_effect=[A.SOURCE+'\n',' M tracked\n']):
   with self.assertRaisesRegex(ValueError,'remain clean'):A.worker_state(Path('/unused'))
 def test_current_tree_pin_drift_refused(self):
  worker=Path(A.P.load(A.P.OUT/'frame.json')['execution_root']);p=A.P.load(A.P.OUT/'prepared_gate.json');p['source_sha256']=dict(p['source_sha256']);p['source_sha256']['rtl/gpu/ot_gpu_rf_service.sv']='wrong'
  with self.assertRaisesRegex(ValueError,'pin mismatch'):A.check_inputs(worker,p)
if __name__=='__main__':unittest.main()
