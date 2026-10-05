"""Program identity and deliberately fabricated unit journals, never RTL evidence."""
import copy,gzip,json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import qwen_rom_program_identity as P
import qwen_rom_program_kv_journal as J
from qwen_rom_persistent_kv_g0 import Owner
from qwen_rom_kv_launch_readiness import instruction
B=P.ROOT/'results/uarch/qwen_rom_program_identity_20261002'
class GateTests(unittest.TestCase):
 @classmethod
 def setUpClass(c):
  c.packet=json.loads(gzip.decompress((B/'retained-programs.json.gz').read_bytes()))
  c.terminal=json.loads(P.TERM.read_text())
  c.image=P.decoded(c.packet['stages']['L0/die0']['program.hex'])
 def test_complete_retained_identity(self):self.assertEqual(P.validate(self.packet,self.terminal)['stages'],148)
 def test_archive_corruption(self):
  p=copy.deepcopy(self.packet);p['stages']['L0/die0']['program.hex']['sha256']='0'*64
  with self.assertRaisesRegex(ValueError,'byte identity'):P.validate(p,self.terminal)
 def test_missing_owner(self):
  p=copy.deepcopy(self.packet);del p['stages']['L35/die3']
  with self.assertRaisesRegex(ValueError,'coverage'):P.validate(p,self.terminal)
 def test_retained_pin_not_manifest_only(self):
  t=copy.deepcopy(self.terminal);t['stage_image_sha256']['L0/die0/program.hex']='0'*64
  with self.assertRaisesRegex(ValueError,'retained program'):P.validate(self.packet,t)
 def test_absent_trace_blocked(self):self.assertEqual(J.check({},None)['status'],'BLOCKED_NO_ACTUAL_ACCEPTED_JOURNAL')
 def gate(self):return J.StageJournal(self.image,Owner(0,0,0,1),0,0)
 def issue(self,g,pc,edge):
  f=J.decode_instruction(g.words[pc]);e=dict(owner=dict(vars(g.owner)),edge=edge,pc=pc,word_sha256=P.sha(f'{g.words[pc]:0256x}'.encode()),kind='accepted_issue',core_issue=1,ticket=pc)
  if f['unit']==J.I.UNIT_ME:
   e.update(me_go=1,fields=J.me_fields(g.words[pc],0,0));e['ib379']=instruction(e['fields'])
  else:e['su_go']=1
  return e
 def populate(self,g):
  for edge,pc in enumerate(g.expected):
   g.event(self.issue(g,pc,edge))
   if pc in g.producer.expected:
    for a in g.producer.expected[pc]:g.event(dict(owner=vars(g.owner),edge=edge,pc=pc,word_sha256=P.sha(f'{g.words[pc]:0256x}'.encode()),kind='kv_lane_write',ticket=pc,address=a,fp32_bits=0,accepted_lane_write=1))
 def test_fixture_complete_512_state(self):
  g=self.gate();self.populate(g);s=g.finish();self.assertEqual(len(bytes.fromhex(s['K_hex'])+bytes.fromhex(s['V_hex'])),512)
 def test_no_zero_fill(self):
  g=self.gate()
  for edge,pc in enumerate(g.expected):g.event(self.issue(g,pc,edge))
  with self.assertRaisesRegex(ValueError,'incomplete producer'):g.finish()
 def test_pc_order(self):
  g=self.gate()
  with self.assertRaisesRegex(ValueError,'PC sequence'):g.event(self.issue(g,g.expected[1],0))
 def test_word_substitution(self):
  g=self.gate();e=self.issue(g,g.expected[0],0);e['word_sha256']='0'*64
  with self.assertRaisesRegex(ValueError,'instruction identity'):g.event(e)
 def test_owner_substitution(self):
  g=self.gate();e=self.issue(g,g.expected[0],0);e['owner']['layer']=1
  with self.assertRaisesRegex(ValueError,'owner identity'):g.event(e)
 def test_ME_field_mutant(self):
  g=self.gate()
  for edge,pc in enumerate(g.expected):
   e=self.issue(g,pc,edge)
   if 'fields' in e:
    e['fields']['xbase']^=1
    with self.assertRaisesRegex(ValueError,'379-bit'):g.event(e)
    return
   g.event(e)
  self.fail('no ME')
 def test_split_aware_decode(self):
  g=self.gate();words=[w for w in g.words if J.decode_instruction(w)['unit']==J.I.UNIT_ME and J.decode_instruction(w)['me_d_tiles']==6]
  self.assertTrue(words)
  for w in words:
   f=J.decode_instruction(w);a=J.me_fields(w,0,8191)
   self.assertEqual(a['tiles'],f['me_tiles']+8191//(16*(6144//(1<<f['me_split'])))+1)
 def test_incomplete_accepted_program(self):
  with self.assertRaisesRegex(ValueError,'accepted program'):self.gate().finish()
 def producer_gate(self):
  g=self.gate()
  for edge,pc in enumerate(g.expected):
   g.event(self.issue(g,pc,edge))
   if pc in g.producer.expected:return g,pc,edge
  self.fail('no producer')
 def lane(self,g,pc,edge):
  return dict(owner=dict(vars(g.owner)),edge=edge,pc=pc,word_sha256=P.sha(f'{g.words[pc]:0256x}'.encode()),kind='kv_lane_write',ticket=pc,address=min(g.producer.expected[pc]),fp32_bits=0,accepted_lane_write=1)
 def test_wrong_producer_ticket(self):
  g,pc,edge=self.producer_gate();e=self.lane(g,pc,edge);e['ticket']=999
  with self.assertRaisesRegex(ValueError,'ticket'):g.event(e)
 def test_duplicate_lane_write(self):
  g,pc,edge=self.producer_gate();e=self.lane(g,pc,edge);g.event(e)
  with self.assertRaisesRegex(ValueError,'unique accepted'):g.event(e)
 def test_unrounded_KV_payload(self):
  g,pc,edge=self.producer_gate();e=self.lane(g,pc,edge);e['fp32_bits']=0x3f800001
  with self.assertRaisesRegex(ValueError,'canonical'):g.event(e)
if __name__=='__main__':unittest.main()
