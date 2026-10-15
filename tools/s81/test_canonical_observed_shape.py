import gzip,json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from canonical_observed_shape import observe,sha
from actual_hardware_ledger import audit

class ObservedShape(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.r=Path(self.t.name)
  self.d=self.r/'die.v';self.p=self.r/'plan.json';self.s=self.r/'stages.json';self.q=self.r/'seq.sv'
  self.d.write_text('module die; wire [14:0] lc; leaf e0(); leaf e1(); cfg c0_0(); cfg c1_0(); seq s0(.lc(lc)); seq s1(.lc(lc)); endmodule')
  self.plan=dict(insts=[['e0','leaf'],['e1','leaf'],['c0_0','cfg'],['c1_0','cfg'],['s0','seq'],['s1','seq']],frames={'0':dict(elems=[[0,'BF',0,'B']]),'1':dict(elems=[[1,'q',0,'L']])})
  self.p.write_text(json.dumps(self.plan));self.stage=dict(PHW_required_by_stage=[10,1],rank_dies=[dict(stage=s,rank=r,die_id=2*s+r) for s in range(2) for r in range(2)],region_bounds=[0,1,2],BF_site_IDs=[0]);self.s.write_text(json.dumps(self.stage))
  self.q.write_text('module seq #(parameter PHW=10, parameter NROM=1)(input wire [PHW+4:0] lc); endmodule')
 def tearDown(self):self.t.cleanup()
 def run_shape(self):return observe(self.d,self.p,self.s,self.q)
 def test_observes_two_pairs_not_canonical_requirement(self):
  x=self.run_shape();self.assertEqual(x['status'],'OBSERVED_SOURCE_AND_CONSTRUCTION_SHAPE');self.assertEqual(x['observed'],dict(field_pairs=2,bf_pairs=1,phase_width=10,stages=2,rank_dies=4));self.assertIsNone(x['emitted_stage_rank_replicas'])
 def test_missing_emitted_pair_rejected(self):
  self.d.write_text(self.d.read_text().replace('leaf e1();',''));x=self.run_shape();self.assertIn('emitted_plan_pair_identity_mismatch',x['failures']);self.assertIsNone(x['observed']['field_pairs'])
 def test_duplicate_pair_rejected(self):
  self.plan['frames']['1']['elems'][0][0]=0;self.p.write_text(json.dumps(self.plan));self.assertEqual(self.run_shape()['status'],'SHAPE_UNPROVEN')
 def test_source_PHW_mutant_rejected_by_actual_connection(self):
  self.q.write_text(self.q.read_text().replace('PHW=10','PHW=9'));x=self.run_shape();self.assertIsNone(x['observed']['phase_width']);self.assertEqual(x['status'],'SHAPE_UNPROVEN')
 def test_CFG_child_removed_rejected(self):
  self.d.write_text(self.d.read_text().replace('cfg c0_0();',''));self.assertIn('missing_emitted_CFG_bank:c0_0',self.run_shape()['failures'])
 def test_duplicate_rank_die_rejected(self):
  self.stage['rank_dies'][1]['die_id']=0;self.s.write_text(json.dumps(self.stage));x=self.run_shape();self.assertIsNone(x['observed']['stages']);self.assertIn('invalid_source_stage_rank_identity',x['failures'])
 def ledger(self,record):
  req=self.r/'required.json';req.write_text(json.dumps(dict(canonical=dict(field_pairs=2,bf_pairs=1,phase_width=10,stages=2,rank_dies=4),operations=[],scope='mechanism')))
  manifest=self.r/'source.f';manifest.write_text('')
  br=self.r/'bind.json';br.write_text(json.dumps(dict(verdict='PASS',die_sha256=sha(self.d))))
  shape=self.r/'shape.json';shape.write_text(json.dumps(record))
  return audit(req,manifest,self.d,br,shape)
 def test_ledger_rejects_legacy_hardcoded_shape(self):
  x=self.ledger(dict(field_pairs=2,bf_pairs=1,phase_width=10,stages=2,rank_dies=4));self.assertIn('canonical_shape_observation_missing_invalid_or_not_die_pinned',x['failures'])
 def test_ledger_valid_observation_still_not_native_qualified(self):
  x=self.ledger(self.run_shape());self.assertEqual(x['verdict'],'PORTS_BOUND_NATIVE_AUDIT_REQUIRED');self.assertFalse(x['release_qualified'])
 def test_ledger_rejects_stale_source_receipt(self):
  record=self.run_shape();self.q.write_text(self.q.read_text().replace('PHW=10','PHW=9'));x=self.ledger(record);self.assertIn('canonical_shape_evidence_missing_or_stale:sequencer_source',x['failures'])
 def test_missing_stage_evidence_keeps_unknown(self):
  self.s.unlink();x=self.run_shape();self.assertIsNone(x['observed']['stages']);self.assertEqual(x['status'],'SHAPE_UNPROVEN')
if __name__=='__main__':unittest.main()
