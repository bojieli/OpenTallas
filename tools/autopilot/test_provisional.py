import importlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).parent))
import autopilot

class Provisional(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();os.environ['AP_DIR']=self.tmp.name
  self.A=importlib.reload(autopilot);self.A.DRY=False
  self.j=dict(id='pending',die='s81',type='io',src='codex/proof@abc123456',host='epyc1',path='/kit',kit='epyc1:/kit',lane='CLOCK',status='WAIT-PARENT',signoff=self.so())
  self.st={'jobs':{'pending':self.j}}
 def tearDown(self):self.tmp.cleanup();os.environ.pop('AP_DIR',None)
 def so(self):return dict(verdict='LOCAL_PASS_NEEDS_PARENT',local_verdict='SIGNED',release_qualified=False,reasons=['io_hold_parent: NEEDS_PARENT'])
 def test_local_pass_is_never_release_signed(self):
  self.assertEqual(self.A.classify({'signoff':self.so()},{'exit':0})[:2],('WAIT-PARENT','parent-receipt-pending'))
 def test_hold_preserves_raw_views_without_failure_or_archive(self):
  self.A.archive=lambda *a:self.fail('archived provisional')
  self.A.start_review=lambda *a:self.fail('rendered false failure')
  self.A.record_failure=lambda *a:self.fail('recorded provisional as failure')
  self.A.after_class(self.st,self.j)
  self.assertFalse(self.j['delete_pending']);self.assertTrue((Path(self.tmp.name)/'provisional.tsv').exists())
  self.assertFalse((Path(self.tmp.name)/'signed.tsv').exists())
 def test_held_receipt_cannot_be_released_by_failure_cleanup(self):
  self.A.failure_resolutions=lambda:{'pending':'operator diagnosis'}
  self.A.hub_procs=lambda p:[]
  self.A.probe_job=lambda j:{'signoff':self.so()}
  self.A.rpy=lambda *a,**kw:self.fail('deleted raw parent inputs')
  self.A.retry_pending(self.st)
  self.assertEqual(self.j['status'],'WAIT-PARENT')
 def test_later_qualified_signed_record_is_archived(self):
  self.A.failure_resolutions=lambda:{};self.A.hub_procs=lambda p:[]
  self.A.probe_job=lambda j:{'signoff':dict(verdict='SIGNED',release_qualified=True)}
  calls=[];self.A.archive=lambda st,j:calls.append(j['status'])
  self.A.retry_pending(self.st)
  self.assertEqual(self.j['status'],'SIGNED');self.assertEqual(calls,['SIGNED'])

if __name__=='__main__':unittest.main()
