import copy,hashlib,json,tempfile,unittest
from pathlib import Path
from tools.qwen_static_schedule.boot import compile_boot
from tools.qwen_static_schedule.calendar import ScheduleError

class Boot(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  def pin(name,data):
   (self.root/name).write_text(data);return {name:hashlib.sha256(data.encode()).hexdigest()}
  source=pin('reset.sv','actual-source-fixture');phase=pin('phase.json',json.dumps(dict(clocks={name:dict(period_fs=100,phase_fs=phase_fs,phase_kind='compensated_phi_minus_R')for name,phase_fs in [('A',0),('B',-20)]})))
  spec=dict(source_sha256=source,parameters={},reset_deassert_edges_after_pin=1,
            child_reset_dependencies=[],data_successor_delta_edges=0,fault_vs_legacy_delta_edges=0)
  self.local=dict(masters=dict(parent=copy.deepcopy(spec),child=copy.deepcopy(spec)))
  self.local['masters']['parent']['child_reset_dependencies']=['child']
  def instance(name,master,parent,clock,traffic):
   return dict(instance=name,master=master,parameters={},reset_from_instance=parent,root_release_fs=0,
               reset_path=[dict(clock=clock,edges=1,net_delay_fs=0,setup_fs=0,cq_fs=1)],
               child_instances=['c']if name=='p'else[],first_traffic_fs=traffic)
  items=[instance('p','parent',None,'A',401),instance('c','child','p','B',401)]
  inventory=pin('inventory.json',json.dumps(dict(instances=items)))
  self.graph=dict(complete=True,missing=[],source_sha256=inventory,instance_inventory_path='inventory.json',
    clocks={name:dict(period_fs=100,phase_fs=phase_fs,phase_kind='compensated_phi_minus_R',source_sha256=phase,profile_path='phase.json')
            for name,phase_fs in [('A',0),('B',-20)]},instances=items)
 def test_actual_compensated_parent_child(self):
  out=compile_boot(self.local,self.graph,self.root)
  self.assertEqual(out['instances']['p']['reset_release_fs'],101)
  self.assertEqual(out['instances']['c']['reset_release_fs'],181)
 def test_missing_physical_graph(self):
  self.graph['missing']=['C17resetrelayages']
  with self.assertRaises(ScheduleError):compile_boot(self.local,self.graph,self.root)
 def test_early_parent_traffic(self):
  self.graph['instances'][0]['first_traffic_fs']=181
  with self.assertRaises(ScheduleError):compile_boot(self.local,self.graph,self.root)
 def test_wrong_phase_convention(self):
  self.graph['clocks']['B']['phase_kind']='common-pin-phase'
  with self.assertRaises(ScheduleError):compile_boot(self.local,self.graph,self.root)
 def test_missing_real_instance(self):
  self.graph['instances'].pop()
  with self.assertRaises(ScheduleError):compile_boot(self.local,self.graph,self.root)
 def test_receipt_value_mismatch(self):
  self.graph['clocks']['B']['phase_fs']=0
  with self.assertRaises(ScheduleError):compile_boot(self.local,self.graph,self.root)
 def test_stale_source(self):
  (self.root/'reset.sv').write_text('stale')
  with self.assertRaises(ScheduleError):compile_boot(self.local,self.graph,self.root)
if __name__=='__main__':unittest.main()
