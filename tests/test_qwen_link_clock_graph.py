import copy
import importlib.util
import json
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('graph',ROOT/'tools/qwen_link_clock_graph.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
G=json.loads((m.DATA/'graph.json').read_text());C=json.loads((m.DATA/'connections.json').read_text())
class ClockGraphTests(unittest.TestCase):
 def test_complete_ownership(self):
  rtl,r=m.emit(G,C)
  self.assertEqual((r['primitives'],r['directional_stream_segments']),(217,442))
  self.assertEqual(rtl.count('.rst_n(link_por_n)'),217)
  self.assertEqual([p['registered_stations'] for p in C['paths']],[54,54,54,55])
  self.assertTrue(all(b['ab_clock_input']!=b['ba_clock_input'] for b in r['bindings']))
 def test_missing_stage_rejected(self):
  c=copy.deepcopy(C);c['pairs'].pop()
  with self.assertRaises(AssertionError):m.emit(G,c)
 def test_duplicated_stage_rejected(self):
  c=copy.deepcopy(C);c['pairs'].append(c['pairs'][0])
  with self.assertRaises(AssertionError):m.emit(G,c)
 def test_north_corner_lane_alias_rejected(self):
  c=copy.deepcopy(C);q=[x for x in c['pairs'] if x['node']=='lc_N'];q[1]['in_lane']=q[0]['in_lane']
  with self.assertRaises(AssertionError):m.emit(G,c)
 def test_truncated_segment_rejected(self):
  g=copy.deepcopy(G);g['edges'][0]['bits']-=1
  with self.assertRaises(AssertionError):m.emit(g,C)
if __name__=='__main__':unittest.main()
