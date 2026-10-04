"""Cold source-pinned replay of the actual directed component result."""
import hashlib,json,unittest
from pathlib import Path
D=Path(__file__).resolve().parent;ROOT=D.parents[3]

class IssuerTerminalTests(unittest.TestCase):
 def test_terminal_exact_source_and_failure_preserved(self):
  t=json.loads((D/'directed-r2/terminal.json').read_text())
  self.assertEqual(t['verdict'],'PASS_DIRECTED_FULL_ISSUER_LEAF')
  self.assertEqual(t['source_sha256'],t['post_source_sha256'])
  for p,h in t['source_sha256'].items():self.assertEqual(hashlib.sha256((ROOT/p).read_bytes()).hexdigest(),h,p)
  self.assertTrue(all(c['pass_'] and c['compile_exit']==0 and c['run_exit']==0 for c in t['cases']))
  old=json.loads((D/'directed-r1-FAIL/terminal.json').read_text())
  self.assertEqual(old['verdict'],'FAIL');self.assertFalse(old['cases'][0]['pass_'])
  self.assertEqual(old['source_sha256'][str((D/'ot_gpu_qwen_full_issuer.sv').relative_to(ROOT))],t['source_sha256'][str((D/'ot_gpu_qwen_full_issuer.sv').relative_to(ROOT))])
  self.assertFalse(t['token']);self.assertFalse(t['installed_bindings']);self.assertFalse(t['physical'])
 def test_fullwidth_tuple_and_protected_storage_prices(self):
  m=json.loads((D/'model.json').read_text());s=(D/'ot_gpu_qwen_full_issuer.sv').read_text()
  self.assertEqual(sum(w for _,w in m['tuple_fields']),239)
  self.assertEqual(m['inventory']['coded_FF_bits'],64*7*72+2*72)
  for term in ('issue_tuple[238:175]==session_id','issue_tuple[174:164]<1737','!unexpected','state[297] && state[298] && state[299]','backend_go_ready','row_barrier_ready'):
   self.assertIn(term,s)
  self.assertIn('whole_reverse_tuple==held_tuple',s);self.assertIn('rf_ack_owner==held_owner',s)
  self.assertIn('next_state[300]=1',s)

if __name__=='__main__':unittest.main()
