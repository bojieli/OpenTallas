"""Identity contract controls; these unit files are not hardware providers."""
import copy,hashlib,json,tempfile,unittest
from pathlib import Path
import kv_pv_cpc_calendar as C

class TrunkIdentityTest(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.groups=Path(self.tmp.name)/'groups.json'
  self.groups.write_text(json.dumps({'landing':[],'unit_context':'identity only'}))
  self.producer=C.ROOT/'tools/qwen_kv_die/pv_landed_calendar.py'
  self.calendar={'input_identity':{'bus_groups_sha256':C.sha(self.groups),'producer_sha256':C.sha(self.producer)}}
 def test_actual_designated_producer(self):
  C.verify_trunk_identity(self.calendar,self.groups,self.producer)
 def test_other_valid_source_hash_rejected(self):
  c=copy.deepcopy(self.calendar)
  c['input_identity']['producer_sha256']=C.sha(Path(C.__file__))
  self.assertRegex(c['input_identity']['producer_sha256'],r'^[0-9a-f]{64}$')
  with self.assertRaisesRegex(ValueError,'reviewed producer'):
   C.verify_trunk_identity(c,self.groups,self.producer)
 def test_changed_producer_rejected(self):
  p=Path(self.tmp.name)/'changed_producer.py';p.write_bytes(self.producer.read_bytes()+b'\n# changed source\n')
  with self.assertRaisesRegex(ValueError,'reviewed producer'):
   C.verify_trunk_identity(self.calendar,self.groups,p)
 def test_changed_bind_rejected(self):
  self.groups.write_text('{"landing":[],"changed":true}')
  with self.assertRaisesRegex(ValueError,'bind identity'):
   C.verify_trunk_identity(self.calendar,self.groups,self.producer)

if __name__=='__main__':unittest.main()
