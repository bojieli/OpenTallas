import importlib.util,importlib.machinery,json,tempfile,unittest,pathlib,subprocess
from unittest.mock import patch
loader=importlib.machinery.SourceFileLoader('heavy',str(pathlib.Path(__file__).resolve().with_name('ot-heavy-reconcile')));spec=importlib.util.spec_from_loader(loader.name,loader);m=importlib.util.module_from_spec(spec);loader.exec_module(m)
class TerminalThreads(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);m.D=self.tmp.name;self.u='oth-ubuntu-completed';self.p=pathlib.Path(m.D);(self.p/'completions').mkdir();(self.p/('res.'+self.u)).write_text(self.u+' 96\n');(self.p/('cthr.'+self.u)).write_text('24\n');(self.p/'completions'/self.u).write_text(self.u+'\t100\t200\t2\n');self.state='LoadState=not-found\nActiveState=inactive\nControlGroup=\n';self.bus='running';self.inventory=[];self.cmd='python3 /lane/completed.py'
 def sh(self,*args):return self.bus if 'is-system-running' in args else self.state
 def fake_run(self,args,**kw):return subprocess.CompletedProcess(args,0,('cid\n' if self.inventory else '') if args[1]=='ps' else json.dumps(self.inventory),'')
 def reap(self):
  with patch.object(m,'sh',self.sh),patch.object(m,'launches',return_value={self.u:(96,self.cmd)}),patch.object(m.subprocess,'run',self.fake_run):return m._reap_completed_thread_charges_locked()
 def kept(self):self.assertEqual(self.reap(),[]);self.assertTrue((self.p/('cthr.'+self.u)).exists())
 def test_terminal_only_charge_archived(self):
  self.assertEqual(self.reap(),[self.u]);self.assertFalse((self.p/('cthr.'+self.u)).exists());self.assertEqual((self.p/('res.'+self.u)).read_text(),self.u+' 96\n');self.assertTrue((self.p/'completions'/self.u).exists());self.assertEqual(json.loads((self.p/'completed-thread-ledger'/(self.u+'.json')).read_text())['threads'],'24')
 def test_active_scope(self):self.state='LoadState=loaded\nActiveState=active\nControlGroup=/scope\n';self.kept()
 def test_pending_without_completion(self):(self.p/'completions'/self.u).unlink();self.kept()
 def test_unknown_completion(self):(self.p/'completions'/self.u).write_text('bad');self.kept()
 def test_bus_failure(self):self.bus='';self.kept()
 def test_scope_lookup_failure(self):self.state='';self.kept()
 def test_detached_unit_container(self):self.inventory=[{'Name':self.u}];self.kept()
 def test_detached_path_container(self):self.cmd='bash /lane/run_kit.sh /lane/actual-kit';self.inventory=[{'HostConfig':{'Binds':['/lane/actual-kit:/work']}}];self.kept()
 def test_docker_failure(self):
  with patch.object(m,'sh',self.sh),patch.object(m.subprocess,'run',side_effect=OSError('daemon unavailable')):self.assertEqual(m._reap_completed_thread_charges_locked(),[])
  self.assertTrue((self.p/('cthr.'+self.u)).exists())
 def test_prior_receipt_preserves_reused_charge(self):self.reap();(self.p/('cthr.'+self.u)).write_text('8\n');self.kept()
if __name__=='__main__':unittest.main()
