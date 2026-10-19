import copy,json,unittest
from pathlib import Path
from . import mu_cold_lists as L
from .mu_cold_prefix import ContractError
P=Path(__file__).resolve().parents[2]/'results/rtl/mu_qwen_1018/admission'
class ColdLists(unittest.TestCase):
 def test_prefix_once_and_repeated_steady(self):
  t=L.encode(prefix=[(10,1,0)],loop_anchor=100,steady=[(8,0,1),(30,1,2)],H=100)
  self.assertEqual(L.played(t,3),[(10,1,0),(108,0,1),(130,1,2),(208,0,1),(230,1,2),(308,0,1),(330,1,2)])
  self.assertEqual(L.played(t,1)[0],(10,1,0)) # rewind0 replays prefix
 def test_long_gap_preserves_minimum_prefetch(self):
  t=L.encode(loop_anchor=L.MAX_DT+1,steady=[(8,0,0)],H=100)
  self.assertEqual(L.played(t,1),[(L.MAX_DT+9,0,0)])
  self.assertTrue(all(w>>12>=4 for w in t['words']))
 def test_no_implicit_phase(self):
  with self.assertRaisesRegex(ContractError,'launch ledger'):L.compile_bound({}, {}, None)
 def test_actual_frame_capacity_and_period_with_declared_diagnostic_binding(self):
  m=json.loads((P/'cold_prefix/manifest.json').read_text());a=json.loads((P/'F16_P2/admission.json').read_text())
  # Explicitly shifted diagnostic phase, not a selected physical FIRST.
  for k in ('first_L0_external_pin',):m['plan'][k]+=10
  for x in m['player_prefix'].values():x['start']+=10
  b=dict(schema='opentallas.mu.list-launch-binding.v1',list_go_reference=m['plan']['head_reference']+10-7,
         raw_L0_minus_steady_anchor=20,reference_start_minus_core_start={c:4 for c in L.CALS},
         admission_done_to_go_guard=4,source_sha256={'fixture':'declared synthetic phase only'},qualified=False)
  r=L.compile_bound(m,a,b)
  self.assertFalse(r['production_bound']);self.assertFalse(r['absolute_FIRST_selected'])
  for c,t in r['tables'].items():
   self.assertLessEqual(t['total_words'],4096)
   self.assertEqual(t['total_words'],3262 if c in m['player_prefix'] else 3261)
   ev=L.played(t,2);pref=1 if c in m['player_prefix'] else 0;n=len(a['link_starts'][c])
   self.assertEqual(len(ev),pref+2*n)
   self.assertEqual([y[0]-x[0] for x,y in zip(ev[pref:pref+n],ev[pref+n:])],[a['H']]*n)
 def test_nominal_phase_cannot_go_before_admission_done(self):
  m=json.loads((P/'cold_prefix/manifest.json').read_text());a=json.loads((P/'F16_P2/admission.json').read_text())
  b=dict(schema='opentallas.mu.list-launch-binding.v1',list_go_reference=m['plan']['head_reference']-7,
         raw_L0_minus_steady_anchor=20,reference_start_minus_core_start={c:4 for c in L.CALS},
         admission_done_to_go_guard=4,source_sha256={'fixture':'declared boundary model'},qualified=False)
  with self.assertRaisesRegex(ContractError,'admission completion'):L.compile_bound(m,a,b)
if __name__=='__main__':unittest.main()
