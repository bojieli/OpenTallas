"""Static preparation gates only; do not classify these as actual RTL execution."""
import json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import prepare_dsrom_upstream_pair_cadence as P
class PrepTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.profiles={k:P.images(k) for k in ('production5','existing_fast8')}
  cls.files=P.package();cls.bench=(ROOT/P.BENCH).read_text()
 def test_source_profile_spacing_and_order(self):
  for name,n in [('production5',40),('existing_fast8',64)]:
   fs,ph,rom=self.profiles[name];self.assertEqual(n,ph['nbeat'])
   beats=[int(s,16) for s in fs['spine_stream.hex'].splitlines()]
   live=[(i,w) for i,w in enumerate(beats) if w&1]
   self.assertEqual(list(range(0,n,n//8)),[i for i,w in live])
   self.assertEqual(list(range(8)),[(w>>9)&7 for i,w in live])
   self.assertTrue(all((w>>1)&255==0 and (w>>12)&3==3 for i,w in live))
 def test_ROM_VM_and_config_equal_profile_inputs(self):
  a,b=(self.profiles[k] for k in ('production5','existing_fast8'))
  self.assertEqual(a[2],b[2])
  for p in ('VM_input.hex','e1.cfg.hex','spine_keys.hex','ROM_input.json'):self.assertEqual(a[0][p],b[0][p])
  cfg=[int(x,16) for x in a[0]['e1.cfg.hex'].splitlines()]
  self.assertEqual(1600,len(cfg));self.assertEqual(256,cfg[0]&65535);self.assertEqual(0x8080,cfg[17]);self.assertEqual(0,cfg[16])
  self.assertEqual(8192,len(a[2][0]));self.assertFalse(any(a[2][1]));self.assertEqual(8,sum(bool(x) for x in a[2][0]))
 def test_independent_exact_quantized_chunk_oracle(self):
  e=P.expected();self.assertEqual('44000000',e['FP32']);self.assertEqual([256.0,256.0],e['chunks'])
  self.assertEqual([32.0]*16,e['block_dots']);self.assertEqual(0,e['err'])
 def test_actual_upstream_wiring_no_FIFO_or_completion_injection(self):
  s=self.bench
  for x in ['ot_v41_rom_adapt #','ot_v41_spine_w17w10 #','ot_v41_pair_w17w10 #','.xs_v(xs_v)','.f_xs_v(xs_v)',".r_v(128'd0)",'x_q[32*k+:32]<=vm[int\'(x_addr)+k]']:
   self.assertIn(x,s)
  self.assertNotIn('force ',s);self.assertNotIn('qpush=',s);self.assertNotIn('npush=',s.replace('npush=%0d',''))
  self.assertIn('STATIC_WITNESS_NOT_REPRODUCED',s);self.assertIn('FIRST_FAULT_DIFFERENT_CAUSE',s)
 def test_full_pair_and_controller_geometry_bound(self):
  for x in ['.R(128)','.VRD(64)','.VAW(19)','.KMAX(6144)','.BST(2)','.NSEG(8)','.NCH(16)','.XF(4)','.FAST(1)','.PP(1)','.BP(0)','.WAKE_REG(1)']:
   self.assertIn(x,self.bench)
  src=P.sources()['rtl/v41rom/ot_v41_rom_elem_w10.sv'];self.assertIn("CUT = 9'b1_0111_1011",src)
  self.assertIn('NCHB = 8',src);self.assertIn('DRAIN = 127',src)
 def test_source_preservation_and_generated_hashes(self):
  m=json.loads((ROOT/P.BASE/'sourceplan.json').read_text())
  for p,h in m['input_source_sha256'].items():self.assertEqual(h,P.sha((ROOT/p).read_bytes()),p)
  self.assertEqual(m['generated_files_sha256'],{p:P.sha(s.encode()) for p,s in self.files.items()})
 def test_expected_assertion_only_DPI_and_marker_semantics(self):
  cpp=self.files['dsrom_upstream_pair_ROM.cpp'];self.assertNotIn('44000000',cpp);self.assertNotIn('expected(',cpp)
  for marker in ['CONTROL_COVERAGE','DUPLICATE_PUBLIC','EMITTED_ORDER','OTHER_FAULT','PUBLIC_ORACLE_DIFFERENCE','CONTROL_FIRST_FAULT']:self.assertIn(marker,self.bench)
  self.assertIn('!pre_overflow || !pre_gate',self.bench)
 def test_fixture_settle_and_tick(self):
  s=self.bench;self.assertIn('#416;',s);self.assertIn('clk=1;#1;',s);self.assertIn('#415;clk=0;#1;',s)
  self.assertEqual(833,416+1+415+1);self.assertIn('rst_n=0;#1;',s);self.assertIn('rst_n=1;#1;',s)
 def test_fresh_only_prepare_and_mutant_hash_refusal(self):
  with tempfile.TemporaryDirectory() as td:
   out=Path(td)/'package';r=P.prepare(out);self.assertFalse(r['compile_authorized']);self.assertFalse(r['simulation_authorized'])
   with self.assertRaises(FileExistsError):P.prepare(out)
  m=json.loads((ROOT/P.BASE/'sourceplan.json').read_text())
  changed=dict(self.files);changed['spine_changed.sv']='module mutant;endmodule'
  self.assertNotEqual(m['generated_files_sha256'],{p:P.sha(t.encode()) for p,t in changed.items()})
if __name__=='__main__':unittest.main()
