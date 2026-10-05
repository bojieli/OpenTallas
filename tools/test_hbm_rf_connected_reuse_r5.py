#!/usr/bin/env python3
"""Read-only inventory and small synthetic copy/mock lifecycle tests; no RTL build."""
import contextlib,json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import hbm_ds_frontend_reuse as I
import prepare_hbm_rf_connected_reuse_r5 as P
import run_hbm_rf_connected_reuse_r5 as R

class Reuse(unittest.TestCase):
 def go(self,p,output='/tmp/no-launch'):
  m=json.loads(p.read_text())['reuse_inventory_pin']
  return dict(schema=R.GO_SCHEMA,admitted=True,source_commit='source',proposal_sha256=I.digest(p),runner_caps=R.CAPS,unit='test.service',admission_record_path='results/newGO.json',reuse_inventory_sha256=m['sha256'],prior_frontend_GO_commit=m['prior_frontend_GO_commit'],frontend_end_sha256=m['frontend_end_sha256'],frontend_argv_sha256=m['frontend_argv_sha256'],frontend_source_bundle_sha256=m['frontend_source_bundle_sha256'],frontend_tool_bundle_sha256=m['frontend_tool_bundle_sha256'],output_path=output)
 def small(self,root):
  root.mkdir()
  for name,data in [('Vconnected.cpp',b'actualsmallcopyfixture'),('Vconnected.mk',b'newrules'),('Vconnected__ver.d',b'oldmetadata')]: (root/name).write_bytes(data)
  return {'object_root':str(root),'files':[{'path':p.name,'bytes':p.stat().st_size,'sha256':I.digest(p)}for p in sorted(root.iterdir())],'file_count':3}
 def test_complete_manifest_shape_and_positive_frontend(self):
  m=json.loads(P.MANIFEST.read_text());self.assertEqual(m['file_count'],11447);self.assertEqual(sum(f['path'].endswith('.cpp')for f in m['files']),11383)
  self.assertEqual(sum(f['bytes']for f in m['files']),1791041356);self.assertEqual(len({f['path']for f in m['files']}),11447)
  self.assertEqual(m['baked_path_audit']['old_output_references'],['Vconnected__ver.d','Vconnected__verFiles.dat'])
 def test_all_source_tool_receipt_pins_current(self):I.verify_inputs(json.loads(P.MANIFEST.read_text()))
 def test_proposal_regenerates_immutable(self):self.assertEqual(P.prepare(),json.loads((P.OUT/P.PROPOSAL).read_text()))
 def test_exclusive_all_file_copy_no_hardlink(self):
  with tempfile.TemporaryDirectory()as d:
   root=Path(d)/'old';m=self.small(root);dest=Path(d)/'new';v=I.copy_inventory(m,dest)
   self.assertEqual(v['files'],3)
   for f in m['files']:
    self.assertEqual((dest/f['path']).read_bytes(),(root/f['path']).read_bytes());self.assertNotEqual((dest/f['path']).stat().st_ino,(root/f['path']).stat().st_ino)
 def test_changed_generated_content_rejected_old_untouched(self):
  with tempfile.TemporaryDirectory()as d:
   root=Path(d)/'old';m=self.small(root);(root/'Vconnected.cpp').write_bytes(b'changed')
   with self.assertRaises(ValueError):I.copy_inventory(m,Path(d)/'new')
   self.assertEqual((root/'Vconnected.cpp').read_bytes(),b'changed')
 def test_missing_extra_symlink_stale_objects_rejected(self):
  for kind in ['missing','extra','symlink','object']:
   with tempfile.TemporaryDirectory()as d:
    root=Path(d)/'old';m=self.small(root)
    if kind=='missing':(root/'Vconnected.cpp').unlink()
    if kind=='extra':(root/'extra.cpp').write_bytes(b'extra')
    if kind=='symlink':(root/'alias.cpp').symlink_to(root/'Vconnected.cpp')
    if kind=='object':(root/'stale.o').write_bytes(b'compiled')
    with self.assertRaises(ValueError):I.copy_inventory(m,Path(d)/'new')
 def test_existing_destination_refused(self):
  with tempfile.TemporaryDirectory()as d:
   root=Path(d)/'old';m=self.small(root);dest=Path(d)/'new';dest.mkdir()
   with self.assertRaises(ValueError):I.copy_inventory(m,dest)
 def test_fresh_go_binds_inventory_receipt_and_source(self):
  path=P.OUT/P.PROPOSAL;go=self.go(path);R.validate_go(go,path,'source')
  for k in ['reuse_inventory_sha256','frontend_end_sha256','prior_frontend_GO_commit','source_commit','proposal_sha256','frontend_argv_sha256','frontend_source_bundle_sha256','frontend_tool_bundle_sha256']:
   with self.assertRaises(ValueError):R.validate_go({**go,k:'changed'},path,'source')
 def test_fresh_qwen_and_no_DS_frontend_command(self):
  cmds=list(R.commands(json.loads((P.OUT/P.PROPOSAL).read_text()),Path('/tmp/no-launch'),'newGO'))
  self.assertEqual([(t,n,s)for t,n,s,a in cmds],[(t,n,s)for t in ('DS','Qwen')for n,s in [('reuse_frontend' if t=='DS' else 'frontend',300),('CXX',600),('simulation',180),('trace',30)]])
  self.assertIn('newGO',cmds[0][3]);self.assertNotIn('--cc',cmds[0][3]);self.assertIn('-GQWEN=1',cmds[4][3])
 def test_cold_make_overrides_and_original_flags(self):
  p=json.loads((P.OUT/P.PROPOSAL).read_text())
  for t in ('DS','Qwen'):
   a=p['commands'][t][1]['argv']
   for x in ('-B','DEPS=','VM_USER_DIR=','OBJCACHE=','OPT_FAST=-O0','OPT_SLOW=-O0','OPT_GLOBAL=-O0'):self.assertIn(x,a)
   self.assertTrue(any(x.startswith('VPATH=')for x in a))
  self.assertFalse(p['resource_plan']['CXX600_is_expected_completion'])
 def test_affinity_exact_with_no_CPU_controller_claim(self):
  args=dict(unit='test.service',cg='/test.service',mem=str(32*1024**3),swap='0',affinity={24,25,26,27},info={'RuntimeMaxUSec':'37min','LimitFSIZE':str(1024**3),'OOMPolicy':'stop'})
  self.assertFalse(R.validate_limits(**args)['cpu_quota_enforced'])
  with self.assertRaises(ValueError):R.validate_limits(**{**args,'affinity':{24,25,26,27,28}})
 def test_make_dependency_override_ignores_absolute_old_targets(self):
  import subprocess
  with tempfile.TemporaryDirectory()as d:
   root=Path(d);old=root/'old-target';old.write_text('immutable')
   (root/'old.d').write_text('all: '+str(old)+'\n'+str(old)+':\n\t/usr/bin/false\n')
   (root/'test.mk').write_text('default: all\nDEPS := $(wildcard *.d)\n-include $(DEPS)\nall:\n\t/usr/bin/true\n')
   result=subprocess.run(['/usr/bin/make','-n','-B','-f','test.mk','DEPS='],cwd=root,capture_output=True,text=True)
   self.assertEqual(result.returncode,0);self.assertIn('/usr/bin/true',result.stdout);self.assertNotIn('/usr/bin/false',result.stdout)
   self.assertEqual(old.read_text(),'immutable')
 def test_changed_source_tool_or_receipt_refused(self):
  with tempfile.TemporaryDirectory()as d:
   root=Path(d);(root/'prior').mkdir();(root/'rtl').mkdir()
   receipt=root/'prior/GO.json';source=root/'rtl/source.sv';tool=root/'tool'
   for p in (receipt,source,tool):p.write_text('pinned')
   m={'prior_output':str(root/'prior'),'prior_receipt_pins':{'GO.json':I.digest(receipt)},'source_sha256':{'rtl/source.sv':I.digest(source)},'tool_files_sha256':{str(tool):I.digest(tool)},'source_root':str(root)}
   with patch.object(I,'ROOT',root):
    I.verify_inputs(m)
    for p in (receipt,source,tool):
     p.write_text('changed')
     with self.assertRaises(ValueError):I.verify_inputs(m)
     p.write_text('pinned')
 def test_copy_timeout_is_failure_without_old_mutation(self):
  with tempfile.TemporaryDirectory()as d:
   root=Path(d)/'old';m=self.small(root)
   with self.assertRaises(TimeoutError):I.copy_inventory(m,Path(d)/'new',limit_s=0)
   for f in m['files']:self.assertEqual(I.digest(root/f['path']),f['sha256'])
 def fake_run(self,fail=False):
  class Proc:
   pid=99999999;returncode=0
   def poll(self):return self.returncode
  with tempfile.TemporaryDirectory()as d:
   out=Path(d)/'new';path=P.OUT/P.PROPOSAL;gopath=Path(d)/'GO.json';go=self.go(path,str(out));gopath.write_text(json.dumps(go));proposal=json.loads(path.read_text())
   def popen(cmd,**kwargs):
    proc=Proc()
    if '--copy' in cmd:
     if fail:proc.returncode=1;return proc
     dst=Path(cmd[cmd.index('--destination')+1]);dst.mkdir(parents=True)
     (dst.parent/'reuse_receipt.json').write_text(json.dumps({'verdict':'PASS_EXCLUSIVE_COMPLETE_FRONTEND_COPY_ONLY','inventory_sha256':go['reuse_inventory_sha256'],'files':11447}))
    if cmd[0].endswith('/Vconnected'):kwargs['stdout'].write(b'CONNECTED_RF_FENCE_PASS\nRESET_RF_FENCE_PASS\n')
    if '--out' in cmd:
     dst=Path(cmd[cmd.index('--out')+1]);q=0 if dst.parent.name=='DS' else 1
     dst.write_text(json.dumps({'verdict':'PASS_DIRECTED_CONNECTED_TRACE_ONLY','cases':[{'qwen':q}for _ in range(4)]}))
    return proc
   with contextlib.ExitStack()as stack:
    stack.enter_context(patch.object(R.G,'git',side_effect=['source','newGO','']))
    stack.enter_context(patch.object(R.subprocess,'check_output',return_value=gopath.read_bytes()))
    stack.enter_context(patch.object(R.P,'prepare',return_value=proposal))
    stack.enter_context(patch.object(R,'validate_cgroup',return_value={'mocked':True}))
    stack.enter_context(patch.object(R.resource,'setrlimit'))
    mock=stack.enter_context(patch.object(R.subprocess,'Popen',side_effect=popen))
    if fail:
     with self.assertRaises(RuntimeError):R.execute(path,gopath,'newGO',out)
     self.assertEqual(mock.call_count,1)
    else:R.execute(path,gopath,'newGO',out);self.assertEqual(mock.call_count,8)
   v=json.loads((out/'verdict.json').read_text());self.assertEqual(v['verdict'],'FAIL_INCOMPLETE'if fail else 'PASS_DIRECTED_NATIVE_DS_QWEN_CONNECTED_ONLY')
   self.assertTrue((out/'DS-reuse_frontend-end.json').exists())
   if not fail:
    for t,n,s,a in R.commands(proposal,out,'newGO'):self.assertTrue((out/f'progress-{t}-{n}.json').exists())
 def test_mocked_complete_reuse_and_Qwen_lifecycle(self):self.fake_run()
 def test_mocked_copy_failure_preserved_before_CXX(self):self.fake_run(True)
if __name__=='__main__':unittest.main(verbosity=2)
