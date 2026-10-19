#!/usr/bin/env python3
import json
from pathlib import Path
import tempfile
import unittest
import qwen_qphase as Q
F=Path(__file__).resolve().parent/'evidence_qphase_1019/inputs'

class QPhase(unittest.TestCase):
 def test_actual_gen_clock_pins_and_missing_safe_ports(self):
  p=Q.make_plan(F/'die.v',F/'fwd_lanes.json','0d4c9808f')
  self.assertEqual(p['lanes']['dvw_dd_wo']['frames'],26)
  self.assertEqual(p['lanes']['dvw_dd_wo']['source_reset_raw'],1266)
  self.assertIn('rly_dvw_dd_wo_25/ckf',p['pins'])
  self.assertIn('native59/ck',p['pins'])
  self.assertIn('SAFE2 native clock port absent from GEN: native59/ck_qbuf',p['blockers'])
  self.assertFalse(p['advance_admitted'])

 def test_different_gen_cannot_join_qready(self):
  with tempfile.TemporaryDirectory() as t:
   q=Path(t)/'qready.json';Q.write(q,dict(inputs=dict(die_v_sha256='wrong',fwd_lanes_sha256='wrong')))
   p=Q.make_plan(F/'die.v',F/'fwd_lanes.json','0d4c9808f',q)
   self.assertIn('Q readiness certificate belongs to a different GEN',p['blockers'])

 def receipt(self,t,corner='tt'):
  t=Path(t);plan=t/'plan.json';target=t/'targets.json';arr=t/'tt.tsv';receipt=t/'tt.json'
  p=Q.make_plan(F/'die.v',F/'fwd_lanes.json','0d4c9808f');Q.write(plan,p)
  Q.write(target,dict(masters={}))
  arr.write_text(''.join(pin+'\t1.0\t0.9\t0.1\n' for pin in p['pins']))
  Q.write(receipt,dict(corner=corner,plan_sha256=Q.sha(plan),arrivals_sha256=Q.sha(arr),pins_with_propagated_clocks=p['pins']))
  return plan,target,arr,receipt

 def test_assumed_views_and_missing_corners_never_admit(self):
  with tempfile.TemporaryDirectory() as t:
   plan,target,arr,receipt=self.receipt(t)
   r=Q.join(plan,target,dict(tt=(arr,receipt)))
   self.assertFalse(r['pin_evidence_complete']);self.assertFalse(r['phase_qualified'])
   self.assertTrue(any('unqualified hard-child' in b for b in r['blockers']))
   self.assertIn('missing actual clock pin measurement: ff',r['blockers'])

 def test_cross_corner_receipt_rejected(self):
  with tempfile.TemporaryDirectory() as t:
   plan,target,arr,receipt=self.receipt(t,corner='ff')
   with self.assertRaisesRegex(ValueError,'identity/corner mismatch'):
    Q.join(plan,target,dict(tt=(arr,receipt)))

 def test_tampered_arrival_rejected(self):
  with tempfile.TemporaryDirectory() as t:
   plan,target,arr,receipt=self.receipt(t)
   with arr.open('a') as f:f.write('unexpected/ck\t1\t1\t1\n')
   with self.assertRaisesRegex(ValueError,'identity/corner mismatch'):
    Q.join(plan,target,dict(tt=(arr,receipt)))

if __name__=='__main__':unittest.main(verbosity=2)
