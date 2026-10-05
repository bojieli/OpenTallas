"""All-rank/fault/pin rejection checks for the additive terminal scope."""
import copy,json,pathlib,sys,tempfile,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'tools'))
import qwen_rom_L0_terminal_source_gate as G
from qwen_rom_program_identity import ROOT,decoded
class TerminalTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.cap=json.loads((ROOT/'results/rtl/qwen_rom_TP4_terminal_20261002/capture.json').read_text())
 def fixture(self,root):
  for r in range(4):
   name=f'L0_die{r}_x.hex';(root/name).write_bytes(decoded(self.cap['files']['actual/'+name]))
  ref=decoded(self.cap['files']['token.log']).decode();line=next(l for l in ref.splitlines() if l.startswith('STAGE L0 done '))
  (root/'token.log').write_text(line+'\nQWEN_ROM_TOKEN_TP2 PASS stages=1 token=0 val=00000000 die1_token=0 cycles=4676 edges=4676\n')
 def test_allfour_checkpoints(self):
  with tempfile.TemporaryDirectory() as t:
   p=pathlib.Path(t);self.fixture(p);r=G.numerical(p,self.cap);self.assertEqual(len(r['checkpoints']),4);self.assertFalse(r['whole_token_repeated'])
 def test_missing_fourth_rank_fails(self):
  with tempfile.TemporaryDirectory() as t:
   p=pathlib.Path(t);self.fixture(p);(p/'L0_die3_x.hex').unlink()
   with self.assertRaises(FileNotFoundError):G.numerical(p,self.cap)
 def test_wrong_fourth_rank_fails(self):
  with tempfile.TemporaryDirectory() as t:
   p=pathlib.Path(t);self.fixture(p);(p/'L0_die3_x.hex').write_text('00000000\n')
   with self.assertRaisesRegex(ValueError,'all-rank'):G.numerical(p,self.cap)
 def test_fault_and_cycle_mutants_fail(self):
  for old,new in [('seq_fault=0','seq_fault=1'),('core_fault=0','core_fault=1'),('coll_fault=0','coll_fault=1'),('end_cyc=4676','end_cyc=4677')]:
   with self.subTest(old=old),tempfile.TemporaryDirectory() as t:
    p=pathlib.Path(t);self.fixture(p);f=p/'token.log';f.write_text(f.read_text().replace(old,new))
    with self.assertRaises(ValueError):G.numerical(p,self.cap)
 def test_extra_layer_fails(self):
  with tempfile.TemporaryDirectory() as t:
   p=pathlib.Path(t);self.fixture(p);f=p/'token.log';f.write_text(f.read_text()+'STAGE L1 done seq_fault=0\n')
   with self.assertRaisesRegex(ValueError,'aperture'):G.numerical(p,self.cap)
 def test_source_pins_and_links_changed_fail(self):
  b={'pins':{str(i):str(i) for i in range(142)},'exclusive_payload_links':{str(i):str(i) for i in range(20)}}
  for k in ('preload_sha256','stage_sha256','original_capture_sha256','runtime_command','runtime_environment'):b[k]=k
  self.assertEqual(G.stable(b,copy.deepcopy(b))['pins'],142)
  for k in ('pins','exclusive_payload_links'):
   a=copy.deepcopy(b);a[k]['0']='mutant'
   with self.assertRaises(ValueError):G.stable(b,a)
if __name__=='__main__':unittest.main()
