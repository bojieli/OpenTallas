"""Fabricated dispatch fixtures test guards only; no actual service credit."""
import copy,gzip,json,pathlib,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'tools'))
import qwen_rom_accepted_stage_journal as D
from qwen_rom_program_identity import decoded,sha
from qwen_rom_program_kv_journal import me_fields
from qwen_rom_kv_launch_readiness import instruction
from qwen_rom_persistent_kv_g0 import Owner
from hdc_qwen_fullshape_isa_w12 import decode_instruction
class DispatchTests(unittest.TestCase):
 @classmethod
 def setUpClass(c):
  p=D.ROOT/'results/uarch/qwen_rom_program_identity_20261002/current-SU1024-AR256-programs-final.json.gz'
  c.bundle=json.loads(gzip.decompress(p.read_bytes()));c.files=c.bundle['stages']['L0/die0']['files']
 def gate(self):return D.DispatchJournal(decoded(self.files['program.hex']),decoded(self.files['segments.hex']),Owner(1,0,0,2),0,0)
 def events(self,g):
  es=[];edge=0
  for i,base in enumerate(g.bases):
   common={'owner':dict(vars(g.stage.owner))}
   es.append(dict(common,kind='segment_start',edge=edge,descriptor_index=i,descriptor_word=f'{g.words[i]:016x}',program_base=base,core_start=1));edge+=1
   end=g.bases[i+1] if i+1<len(g.bases) else len(g.stage.words)
   for pc in g.stage.expected:
    if not base<=pc<end:continue
    word=g.stage.words[pc];f=decode_instruction(word)
    e=dict(common,kind='accepted_issue',edge=edge,pc=pc,core_pc=pc-base,program_base=base,word_sha256=sha(f'{word:0256x}'.encode()),ticket=pc,core_issue=1)
    if f['unit']==1:e.update(me_go=1,fields=me_fields(word,0,0));e['ib379']=instruction(e['fields'])
    else:e['su_go']=1
    es.append(e)
    if pc in g.stage.producer.expected:
     for a in sorted(g.stage.producer.expected[pc]):es.append(dict(common,kind='kv_lane_write',edge=edge,pc=pc,ticket=pc,word_sha256=e['word_sha256'],address=a,fp32_bits=0,accepted_lane_write=1))
    edge+=1
   es.append(dict(common,kind='segment_done',edge=edge,descriptor_index=i,core_done=1));edge+=1
  es.append(dict(common,kind='KV_state_snapshot',edge=edge,K_hex='00'*256,V_hex='00'*256))
  return es
 def run_events(self,events):
  g=self.gate()
  for e in events:g.event(e)
  return g.finish()
 def test_fixture_dispatch_full_state(self):
  g=self.gate();r=self.run_events(self.events(g));self.assertEqual(r['accepted_KV_ME_count'],2);self.assertEqual(len(r['segment_receipts']),3)
 def test_missing_actual_journal(self):self.assertIn('BLOCKED',D.check(self.bundle,None)['status'])
 def test_core_pc_is_not_absolute_pc(self):
  es=self.events(self.gate());e=next(e for e in es if e['kind']=='accepted_issue' and e['program_base']!=0);e['core_pc']=e['pc']
  with self.assertRaisesRegex(ValueError,'plus program base'):self.run_events(es)
 def test_wrong_descriptor_word(self):
  es=self.events(self.gate());es[0]['descriptor_word']='0'*16
  with self.assertRaisesRegex(ValueError,'descriptor dispatch'):self.run_events(es)
 def test_issue_without_start(self):
  es=self.events(self.gate())[1:]
  with self.assertRaisesRegex(ValueError,'without actual'):self.run_events(es)
 def test_early_done(self):
  es=self.events(self.gate());done=next(e for e in es if e['kind']=='segment_done');done=copy.deepcopy(done);done['edge']=1
  with self.assertRaisesRegex(ValueError,'before accepted'):self.run_events([es[0],done])
 def test_incomplete_state_before_KV_consumer(self):
  es=[e for e in self.events(self.gate()) if e['kind']!='kv_lane_write']
  with self.assertRaisesRegex(ValueError,'incomplete producer'):self.run_events(es)
 def test_snapshot_payload_substitution(self):
  es=self.events(self.gate());es[-1]['K_hex']='01'*256
  with self.assertRaisesRegex(ValueError,'snapshot differs'):self.run_events(es)
 def test_missing_snapshot(self):
  with self.assertRaisesRegex(ValueError,'incomplete descriptor/state'):self.run_events(self.events(self.gate())[:-1])
 def test_repeated_descriptor(self):
  es=self.events(self.gate());e=next(e for e in es[1:] if e['kind']=='segment_start');e['descriptor_index']=0
  with self.assertRaisesRegex(ValueError,'dispatch sequence'):self.run_events(es)
if __name__=='__main__':unittest.main()
