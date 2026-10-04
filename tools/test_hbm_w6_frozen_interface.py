import tempfile, unittest
from pathlib import Path
from unittest.mock import patch
import hbm_w6_frozen_interface as F
class FrozenTests(unittest.TestCase):
 def test_original(self):
  r=F.verify();self.assertFalse(r['actual_join_qualified']);self.assertEqual(sum(x['bits'] for x in r['identity_layout_MSB_to_LSB']),55)
 def test_ACK_origins_distinct(self):
  p=F.verify()['ports']
  for name in ['host_ack_identity','simd_ack_retire_identity','consumer_identity','child_reverse_identity','parent_reverse_identity','reverse_CDC_identity','drain_rsp_identity']:
   self.assertEqual(p[name],dict(direction='input',bits=55))
 def test_reset_and_drain_scope(self):
  p=F.verify()['ports'];self.assertEqual(p['alldrain_live']['bits'],9)
  for name in ['por_n','rst_n','drain_rsp_has_owner','drain_rsp_reset_scope']:self.assertEqual(p[name],dict(direction='input',bits=1))
 def test_defaultoff_held_outputs(self):
  r=F.verify();self.assertEqual(r['default_ENABLE'],0)
  for name in ['visible_identity','retire_identity','drain_req_identity']:self.assertEqual(r['ports'][name],dict(direction='output',bits=55))
 def test_mutants_source_refused(self):
  read=Path.read_bytes
  mutations=[('host_ack_identity','epoch_ack_identity'),('[54:0]','[53:0]'),('simd_ack_retire_valid','host_ack_retire_valid'),('alldrain_live','historical_drain'),("ENABLE=1'b0","ENABLE=1'b1"),('por_n','local_por')]
  for before,after in mutations:
   with self.subTest(mutation=before):
    def changed(p):
     raw=read(p)
     return raw.replace(before.encode(),after.encode()) if p==F.ROOT/F.RTL else raw
    with patch.object(Path,'read_bytes',changed),self.assertRaisesRegex(ValueError,'source drift'):F.verify()
 def test_missing_peer_source_refused(self):
  with tempfile.TemporaryDirectory() as t,self.assertRaises(FileNotFoundError):F.verify(t)
 def test_no_launch_or_write(self):
  with patch('subprocess.Popen',side_effect=AssertionError('launch')),patch.object(Path,'write_bytes',side_effect=AssertionError('mutation')):F.verify()
if __name__=='__main__':unittest.main()
