"""Preflight field/pin mutants only; no checkpoint arithmetic or service launch."""
import copy
import hashlib
import json
from pathlib import Path
import resource
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import qwen_kv_campaign_run as C
HELPERS=['qwen_kv_observation_adapter.py','qwen_kv_observation_verify.py','qwen_kv_observed_native.py','qwen_kv_reference_u8.py','qwen_kv_released_operator_gate.py','qwen_kv_campaign_prepare.py','qwen_kv_campaign_run.py','qwen_kv_campaign_launcher.py','qwen_native_terminal_replay.py']
class PreflightTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.base=Path(self.tmp.name);self.orig=self.base/'original';self.add=self.base/'additive';self.archive=self.base/'archive'
  for p in [self.orig/'tools',self.add/'tools',self.archive/'native']:p.mkdir(parents=True)
  for name in HELPERS:(self.add/'tools'/name).write_text(name)
  (self.orig/'tools/arithmetic.py').write_text('immutable');(self.archive/'capture.npy').write_bytes(b'captured');(self.archive/'native/terminal.json').write_text('{}');(self.archive/'native/post_execution_comparisons.json').write_text('[]')
  original={'tools/arithmetic.py':C.sha(self.orig/'tools/arithmetic.py')};(self.archive/'GO.json').write_text(json.dumps(dict(source_commit='870c5fe581b768df28dd2998b2d0aecc24510c23',source_sha256=original)))
  self.p=dict(original_source_root=str(self.orig),original_source_commit='870c5fe581b768df28dd2998b2d0aecc24510c23',additive_source_root=str(self.add),additive_source_commit='additive',additive_source_sha256={str((self.add/'tools'/n).resolve()):C.sha(self.add/'tools'/n)for n in HELPERS},original_source_sha256=original,capture_file_sha256={str(self.archive/'capture.npy'):C.sha(self.archive/'capture.npy')},native_terminal_sha256=C.sha(self.archive/'native/terminal.json'),comparison_sha256=C.sha(self.archive/'native/post_execution_comparisons.json'),resource_model=dict(proposed_memory_reservation_bytes=34359738368))
  self.a=dict(additive_source_commit='additive',admission_record_path='GO.json',admitted=True,native_decode=False,production_SCORES_PV_arithmetic=False,native_archive=str(self.archive),extra_file_sha256={},memory_reservation_bytes=34359738368,FSIZE='unlimited',AS='unlimited',wall_limit=None,output_parent=str(self.base),disk_reserve_bytes=0,priced_incremental_output_bytes=0,minimum_memavailable_bytes=0,cpus=list(range(8)),unit='unit')
 def run_case(self,p=None,a=None,runtime=False,affinity=None,limits=None):
  p=p or self.p;a=a or self.a
  def command(args,**kwargs):
   if args[:2]==['git','status']:return b''
   if args[:2]==['git','show']:return json.dumps(self.a).encode()
   return 'infinity\n'
  with patch.object(C,'head',side_effect=lambda r:self.p['original_source_commit']if Path(r)==self.orig else 'additive'),patch.object(C.subprocess,'check_output',side_effect=command),patch.object(C.os,'sched_getaffinity',return_value=set(affinity or range(8))),patch.object(C.resource,'getrlimit',side_effect=limits or (lambda k:(resource.RLIM_INFINITY,resource.RLIM_INFINITY))):return C.preflight(p,a,'GO',runtime)
 def test_readonly_positive(self):self.assertEqual(self.run_case()['status'],'PASS_SOURCE_RESOURCE_PREFLIGHT')
 def test_helper_pin_mutant(self):
  (self.add/'tools'/HELPERS[0]).write_text('changed')
  with self.assertRaisesRegex(ValueError,'helper pin'):self.run_case()
 def test_missing_helper_inventory(self):
  p=copy.deepcopy(self.p);p['additive_source_sha256'].pop(next(iter(p['additive_source_sha256'])))
  with self.assertRaisesRegex(ValueError,'inventory'):self.run_case(p)
 def test_original_frame_subset_refused(self):
  p=copy.deepcopy(self.p);p['original_source_sha256']={}
  with self.assertRaisesRegex(ValueError,'original admitted frame'):self.run_case(p)
 def test_capture_change_refused(self):
  (self.archive/'capture.npy').write_bytes(b'changed')
  with self.assertRaisesRegex(ValueError,'capture pin'):self.run_case()
 def test_GO_change_refused(self):
  a=copy.deepcopy(self.a);a['memory_reservation_bytes']=1
  with self.assertRaisesRegex(ValueError,'exact GO'):self.run_case(a=a)
 def test_real_affinity_required(self):
  with self.assertRaisesRegex(ValueError,'kernel affinity'):self.run_case(runtime=True,affinity=[1,2])
 def test_process_AS_cap_refused(self):
  with self.assertRaisesRegex(ValueError,'process cap'):self.run_case(runtime=True,limits=lambda k:(3*1024**3,3*1024**3)if k==resource.RLIMIT_AS else (resource.RLIM_INFINITY,resource.RLIM_INFINITY))
 def test_original_SOURCE_cannot_drift(self):
  p=copy.deepcopy(self.p);p['original_source_commit']='changed'
  with self.assertRaisesRegex(ValueError,'historical frame'):self.run_case(p)

 def test_runtime_has_no_memory_or_swap_cap_requirement(self):
  read=Path.read_text
  def read_metadata(path,*args,**kwargs):
   if path.name in ('memory.max','memory.swap.max'):raise AssertionError('memory/swap cap must not be required')
   return read(path,*args,**kwargs)
  with patch.object(Path,'read_text',read_metadata):self.assertEqual(self.run_case(runtime=True)['status'],'PASS_SOURCE_RESOURCE_PREFLIGHT')
 def test_scheduling_reservation_must_match_model(self):
  p=copy.deepcopy(self.p);p['resource_model']['proposed_memory_reservation_bytes']=1
  with self.assertRaisesRegex(ValueError,'scheduling reservation'):self.run_case(p=p)
