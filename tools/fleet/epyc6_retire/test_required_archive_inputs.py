"""Exact recovered-input C3 checks, using the actual local hash verifier (no fleet I/O)."""
import importlib.util,json,pathlib,subprocess,sys,tempfile,unittest,hashlib
from unittest.mock import patch
HERE=pathlib.Path(__file__).parent
class RequiredArchiveInputs(unittest.TestCase):
 def setUp(self):
  spec=importlib.util.spec_from_file_location('retire_inputs',HERE/'epyc6_retire.py');self.m=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.m)
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.base=pathlib.Path(self.tmp.name);self.m.STATE=str(self.base);self.m.DEST=str(self.base/'archive');self.root=pathlib.Path(self.m.DEST)/'recovered';self.root.mkdir(parents=True);(self.root/'source.sv').write_bytes(b'old');self.row=['source.sv',3,hashlib.sha256(b'old').hexdigest()]
  self.jobs=['hcoll_v7_tkm_tile_e86v4b-v4b-39d901240','qfd_dv_s5_sc2b-sc2bk-dc13647fb','s81sl_ve_r5-s81sl_ve_r5-f51f4ec42'];self.job=self.jobs[0]
  self.cfg={'jobs':{j:{'missing_inputs':[],'roots':{str(self.root):[self.row]}} for j in self.jobs}}
  def verify(mode,payload):
   r=subprocess.run([sys.executable,str(HERE/'remote_verify.py'),mode],input=json.dumps(payload),text=True,capture_output=True,check=True);return json.loads(r.stdout)
  self.patcher=patch.object(self.m,'agi_py',side_effect=verify);self.patcher.start();self.addCleanup(self.patcher.stop)
 def save(self): (self.base/'required_archive_inputs.json').write_text(json.dumps(self.cfg))
 def test_exact_bytes_pass_and_record_verification(self):
  self.save();self.assertEqual(self.m.check_required_archive_inputs(),[]);self.assertTrue((self.base/'required_archive_inputs_verified.json').exists())
 def test_absent_configuration_waits(self):self.assertTrue(self.m.check_required_archive_inputs())
 def test_empty_configuration_waits(self):self.cfg={'jobs':{}};self.save();self.assertTrue(self.m.check_required_archive_inputs())
 def test_known_route_input_gap_waits_before_hashing(self):
  self.cfg['jobs'][self.job]['missing_inputs']=['post-transform library binding'];self.save();self.assertTrue(self.m.check_required_archive_inputs());self.m.agi_py.assert_not_called()
 def test_same_size_corruption_waits(self):
  self.save();(self.root/'source.sv').write_bytes(b'new');self.assertTrue(self.m.check_required_archive_inputs())
 def test_missing_file_waits(self):
  self.save();(self.root/'source.sv').unlink();self.assertTrue(self.m.check_required_archive_inputs())
 def test_missing_result_waits(self):
  self.save();self.m.agi_py.side_effect=lambda *a:{};self.assertTrue(self.m.check_required_archive_inputs())
 def test_empty_root_waits(self):
  self.cfg['jobs'][self.job]['roots'][str(self.root)]=[];self.save();self.assertTrue(self.m.check_required_archive_inputs())
 def test_parent_traversal_refused(self):
  self.row[0]='../source.sv';self.save();self.assertTrue(self.m.check_required_archive_inputs());self.m.agi_py.assert_not_called()
 def test_archive_root_outside_destination_refused(self):
  self.cfg['jobs'][self.job]['roots']={'/unrelated':[self.row]};self.save();self.assertTrue(self.m.check_required_archive_inputs());self.m.agi_py.assert_not_called()
 def test_omitted_known_job_waits(self):
  del self.cfg['jobs'][self.jobs[-1]];self.save();self.assertTrue(self.m.check_required_archive_inputs());self.m.agi_py.assert_not_called()
 def test_bool_size_waits(self):
  self.row[1]=True;self.save();self.assertTrue(self.m.check_required_archive_inputs());self.m.agi_py.assert_not_called()
 def test_malformed_shapes_wait(self):
  import copy
  original=copy.deepcopy(self.cfg)
  for entry in [None,[],{'missing_inputs':[],'roots':[]},{'missing_inputs':'','roots':{}},{'missing_inputs':[],'roots':{str(self.root):[None]}},{'missing_inputs':[],'roots':{str(self.root):[[None,3,'a'*64]]}},{'missing_inputs':[],'roots':{str(self.root):['bad-row']}}]:
   with self.subTest(entry=entry):
    self.cfg=copy.deepcopy(original);self.cfg['jobs'][self.job]=entry;self.save();self.assertTrue(self.m.check_required_archive_inputs())
if __name__=='__main__':unittest.main()
