#!/usr/bin/env python3
"""Runtime demand, qualified-copy and disjoint calendar controls; no DUT execution."""
import contextlib,hashlib,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import prepare_hbm_runtime_calibration_r8 as P
import hbm_DS_binary_reuse_r8 as I
import run_hbm_runtime_calibration_r8 as R

class RuntimeCalibration(unittest.TestCase):
 def test_measured_cycle_projection(self):
  m=json.loads(P.MODEL.read_text());self.assertEqual(m['expected_DS_finish_cycle'],37219);self.assertEqual(m['proposed_DS_simulation_cap_s'],6780);self.assertEqual(m['DS_SIMD_operations'],1028);self.assertEqual(m['last_complete_alias'],[3,0,250,9683]);self.assertIsNone(m['Qwen']['runtime_measurement'])
 def test_source_geometry_and_independent_phases(self):
  base=json.loads(P.BASE.read_text())
  with patch.object(P.I,'verify'):
   ds=P.derive(base,'DS');q=P.derive(base,'Qwen')
  self.assertEqual(ds['source_sha256'],q['source_sha256']);self.assertEqual(ds['source_sha256'],base['source_sha256'])
  self.assertEqual([x['phase']for x in ds['commands']['DS']],['reuse_binary','simulation','trace']);self.assertEqual([x['phase']for x in q['commands']['Qwen']],['frontend','CXX'])
  self.assertIn('-j16',q['commands']['Qwen'][1]['argv']);self.assertIn('-B',q['commands']['Qwen'][1]['argv']);self.assertIn('AR=/usr/bin/ar --thin',q['commands']['Qwen'][1]['argv'])
 def test_disjoint_cpu_masks_and_unchanged_memory_file_caps(self):
  ds=P.caps_for('DS');q=P.caps_for('Qwen');self.assertFalse(set(ds['cpus'])&set(q['cpus']));self.assertEqual(set(ds['cpus'])|set(q['cpus']),{0}|set(range(8,24)))
  for c in [ds,q]:self.assertEqual(c['memory_bytes'],32*1024**3);self.assertEqual(c['swap_bytes'],0);self.assertEqual(c['per_file_bytes'],1024**3);self.assertEqual(c['aggregate_output_bytes'],8*1024**3)
 def small(self,root):
  src=root/'old';src.write_bytes(b'\x7fELFcomplete fixture');return dict(binary=dict(path=str(src),bytes=src.stat().st_size,sha256=hashlib.sha256(src.read_bytes()).hexdigest(),mode=0o755))
 def test_exclusive_complete_binary_copy(self):
  with tempfile.TemporaryDirectory()as d:
   root=Path(d);m=self.small(root);dst=root/'new/obj/Vconnected';v=I.copy_binary(m,dst);self.assertEqual(v['verdict'],'PASS_EXCLUSIVE_QUALIFIED_COMPLETE_DS_ELF_COPY');self.assertEqual(dst.read_bytes(),(root/'old').read_bytes());self.assertNotEqual(dst.stat().st_ino,(root/'old').stat().st_ino);self.assertFalse(v['objects_PCH_archive_reused'])
 def test_binary_tamper_refused(self):
  with tempfile.TemporaryDirectory()as d:
   root=Path(d);m=self.small(root);(root/'old').write_bytes(b'\x7fELFchanged')
   with self.assertRaises(ValueError):I.copy_binary(m,root/'new')
 def test_existing_destination_refused(self):
  with tempfile.TemporaryDirectory()as d:
   root=Path(d);m=self.small(root);dst=root/'new';dst.write_bytes(b'untouched')
   with self.assertRaises(ValueError):I.copy_binary(m,dst)
   self.assertEqual(dst.read_bytes(),b'untouched')
 def test_relocated_execution_refused(self):
  m=json.loads(P.MANIFEST.read_text());m['source_root']='/tmp/refused-relocated-H1-runtime-root'
  with self.assertRaisesRegex(ValueError,'source root changed'):I.verify(m)
 def test_actual_build_and_runtime_bindings(self):
  I.verify(json.loads(P.MANIFEST.read_text()),require_root=False)
 def test_target_runtime_caps_enforced(self):
  for t,cap in [('DS','1h 58min 30s'),('Qwen','35min 30s')]:
   with patch.object(R,'CAPS',P.caps_for(t)):
    info=dict(RuntimeMaxUSec=cap,LimitFSIZE=str(1024**3),OOMPolicy='stop');R.validate_limits('a.service','/a.service',str(32*1024**3),'0',P.caps_for(t)['cpus'],info)
    with self.assertRaises(ValueError):R.validate_limits('a.service','/a.service',str(32*1024**3),'0',range(0,24),info)
 def test_mocked_independent_lifecycles(self):
  class Proc:
   pid=9999999;returncode=0
   def poll(self):return 0
  for target in ('DS','Qwen'):
   with tempfile.TemporaryDirectory()as d:
    root=Path(d);out=root/'output'
    with patch.object(P.I,'verify'):p=P.derive(json.loads(P.BASE.read_text()),target)
    proposal=root/'proposal.json';proposal.write_text(json.dumps(p));pin=p['reuse_inventory_pin']
    go=dict(schema=P.GO_SCHEMA,admitted=True,target=target,source_commit='source',proposal_sha256=R.G.sha(proposal),runner_caps=P.caps_for(target),unit='test.service',admission_record_path='results/newGO.json',output_path=str(out),reuse_inventory_sha256=pin['sha256'],**{k:pin[k]for k in ('prior_frontend_GO_commit','frontend_end_sha256','frontend_argv_sha256','frontend_source_bundle_sha256','frontend_tool_bundle_sha256')},**{k:p[k]for k in ('calibration_model_sha256','prior_failure_sha256','prior_r2_failure_sha256','runtime_model_sha256','qualified_binary_manifest_sha256')})
    gopath=root/'GO.json';gopath.write_text(json.dumps(go))
    def popen(cmd,**kwargs):
     folder=out/target
     if '--destination' in cmd:(folder/'reuse_binary_receipt.json').write_text(json.dumps(dict(verdict='PASS_EXCLUSIVE_QUALIFIED_COMPLETE_DS_ELF_COPY')))
     if '--object-root' in cmd:(folder/'CXX_archive_receipt.json').write_text(json.dumps(dict(verdict='PASS_COLD_CXX_EXACT_THIN_ARCHIVE_ONLY')))
     if cmd[0].endswith('/Vconnected'):kwargs['stdout'].write(b'CONNECTED_RF_FENCE_PASS\nRESET_RF_FENCE_PASS\n')
     if '--out' in cmd:Path(cmd[cmd.index('--out')+1]).write_text(json.dumps(dict(verdict='PASS_DIRECTED_CONNECTED_TRACE_ONLY',cases=[dict(qwen=0)for _ in range(4)])))
     return Proc()
    with contextlib.ExitStack()as stack:
     stack.enter_context(patch.object(R.G,'git',side_effect=['source','GO','']))
     stack.enter_context(patch.object(R.subprocess,'check_output',return_value=gopath.read_bytes()))
     stack.enter_context(patch.object(R.P,'prepare_target',return_value=p))
     stack.enter_context(patch.object(R,'validate_cgroup',return_value=dict(mocked=True)))
     stack.enter_context(patch.object(R.resource,'setrlimit'))
     proc=stack.enter_context(patch.object(R.subprocess,'Popen',side_effect=popen))
     R.execute(proposal,gopath,'GO',out);self.assertEqual(proc.call_count,3 if target=='DS' else 2)
    verdict=json.loads((out/'verdict.json').read_text());self.assertEqual(verdict['connected_measurement'],target=='DS');self.assertEqual(verdict['verdict'],'PASS_DIRECTED_NATIVE_DS_CONNECTED_ONLY'if target=='DS'else'PASS_NATIVE_QWEN_BUILD_ONLY')
if __name__=='__main__':unittest.main()
