import json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from qwen_embedding_ingress_collect import held_route_inputs
class Held(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.run=Path(self.t.name);(self.run/'src').mkdir();(self.run/'src/SOURCE_COMMIT').write_text('1'*40+'\n')
  self.route=self.run/'routes/test_pad';self.orfs=self.route/'work/orfs';self.logs=self.orfs/'logs/asap7/top/base';self.logs.mkdir(parents=True)
  (self.route/'status').write_text('flow_rc=0\ncorner_rc=0\n');(self.route/'corner_sta.json').write_text(json.dumps(dict(orfs_dir=str(self.orfs))));self.drc=self.logs/'5_2_route.json';self.drc.write_text(json.dumps({'detailedroute__route__drc_errors':0}))
  self.state=dict(name='test-pad',run=str(self.run),spec=dict(source=dict(commit='1'*40),verdict=dict(corner_sta='{RUN}/routes/{LABEL}/corner_sta.json')))
 def tearDown(self):self.t.cleanup()
 def test_without_daemon_metrics_or_verdict(self):
  before=json.dumps(self.state,sort_keys=True);p,o,a=held_route_inputs(self.state);self.assertEqual(o,self.orfs);self.assertEqual(a['qualification_mode'],'held_route_readonly');self.assertEqual(before,json.dumps(self.state,sort_keys=True))
 def test_failure_rc(self):
  (self.route/'status').write_text('flow_rc=0\ncorner_rc=1\n')
  with self.assertRaises(ValueError):held_route_inputs(self.state)
 def test_nonzero_drc(self):
  self.drc.write_text(json.dumps({'detailedroute__route__drc_errors':1}))
  with self.assertRaises(ValueError):held_route_inputs(self.state)
 def test_wrong_source(self):
  (self.run/'src/SOURCE_COMMIT').write_text('2'*40)
  with self.assertRaises(ValueError):held_route_inputs(self.state)
 def test_other_route(self):
  (self.route/'corner_sta.json').write_text(json.dumps(dict(orfs_dir='/tmp/other')))
  with self.assertRaises(ValueError):held_route_inputs(self.state)
 def test_missing_drc(self):
  self.drc.unlink()
  with self.assertRaises(ValueError):held_route_inputs(self.state)
if __name__=='__main__':unittest.main()
