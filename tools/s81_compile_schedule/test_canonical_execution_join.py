"""Mechanism fixtures only; none of these synthetic programmes qualify a chip."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from canonical_execution_join import join

class CanonicalJoinTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root/'native.sv').write_text('// synthetic compiler mechanism fixture\n')
        self.evidence = [dict(path='native.sv',sha256=hashlib.sha256((self.root/'native.sv').read_bytes()).hexdigest())]
        self.canonical = dict(rank_programme_bindings=[dict(stage=s,rank=r,die_id=4*s+r)
                                                       for s in range(81) for r in range(4)])
        self.catalogue = dict(source_SU_nodes=[dict(node='mtp.I0',scope='mtp',template_sha256='1'*64)])
        self.program = dict(stage='fixture',ops=[dict(id='native_job',eng='su',port=1,start=0,end=10,preds=[])])
        self.binding = dict(stage='fixture',tensors={'input':dict(base_row=256,nrows=1,source='external_input',consumers=['native_job'],evidence=self.evidence)},jobs=dict(native_job=dict(engine='su',implementation='native_rtl',
            physical_instance='su0',endpoint='fixture',client='su',tag=0,duration_cycles=10,
            phase_period_stream=1,start_phase_stream=0,evidence=self.evidence,accesses=[dict(kind='read',tensor='input',row_offset=0,slot=0,issue_cycle=1,ingress_cycle=2,bank_enqueue_cycle=2,service_cycle=3,response_cycle=4,deadline_cycle=8)])))
        self.contract = dict(stream_period_ps=1,vm_period_ps=1,stream_phase_ps=0,vm_phase_ps=0,banks=32,
            bank_ops_per_cycle=1,read_ingress_per_cycle=16,write_ingress_per_cycle=16,request_min_ps=1,
            read_min_ps=1,commit_min_ps=1,slot_capacity={'su/read/0':4},client_capacity={'su':4},bank_queue_capacity=4,measured_native_bounds=True)
        self.inventory = dict(schema='opentallas.s81.elaborated-leaf-instances.v1', source_evidence=self.evidence,
                              instances=[dict(instance=f'{role}{i}',role=role,die_id=i) for i in range(324) for role in ('su','vm')])
        self.manifest = dict(native_instance_inventory=self.pin('inventory.json', self.inventory),rank_programmes=[])
        for s in range(81):
            for r in range(4):
                i=4*s+r
                binding=copy.deepcopy(self.binding);binding['jobs']['native_job']['physical_instance']=f'su{i}'
                record=dict(stage=s,rank=r,die_id=i,su_instance=f'su{i}',vm_instance=f'vm{i}',core_epoch=0,
                    program=self.pin('program.json', self.program),binding=self.pin(f'binding{i}.json',binding),
                    vm_contract=self.pin('contract.json',self.contract),source_operations=dict(native_job=[
                        dict(node='mtp.I0',template_sha256='1'*64)]))
                # Only one actual stage executes a given source op/rank. Other
                # fixture stages use distinct catalogue operations.
                name=f'stage{s}.I0'
                if s:
                    self.catalogue['source_SU_nodes'].append(dict(node=name,scope=s,template_sha256='1'*64)) if r==0 else None
                    record['source_operations']['native_job'][0]['node']=name
                self.manifest['rank_programmes'].append(record)
        self.inventory['source_operation_homes']=[dict(node=('mtp.I0' if s==0 else f'stage{s}.I0'),
            stage=s,rank=r,die_id=4*s+r,template_sha256='1'*64,physical_instance=f'su{4*s+r}')
            for s in range(81) for r in range(4)]
        self.manifest['native_instance_inventory']=self.pin('inventory.json',self.inventory)
    def pin(self,name,value):
        path=self.root/name;path.write_text(json.dumps(value,sort_keys=True))
        return dict(path=name,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    def run_join(self):
        return join(self.canonical,self.catalogue,self.manifest,self.root)
    def reasons(self,r):
        return [v['kind'] for v in r['violations']]
    def test_exact_local_source_home_calendar_join_still_not_fullchip_dispatch(self):
        r=self.run_join();self.assertTrue(r['local_programmes_ready'],r['violations'][:2])
        self.assertEqual(r['covered_rank_operations'],324)
        self.assertEqual(r['rank_programmes_compiled'],324)
        self.assertFalse(r['dispatch_eligible']);self.assertFalse(r['qualified'])
    def test_actual_same_hierarchy_name_on_distinct_dies_is_legal(self):
        for instance in self.inventory['instances']:
            instance['instance']=instance['role']
        for home in self.inventory['source_operation_homes']:
            home['physical_instance']='su'
        self.manifest['native_instance_inventory']=self.pin('inventory.json',self.inventory)
        for record in self.manifest['rank_programmes']:
            record.update(su_instance='su',vm_instance='vm')
            binding=copy.deepcopy(self.binding)
            binding['jobs']['native_job']['physical_instance']='su'
            record['binding']=self.pin('repeated_hierarchy_binding.json',binding)
        self.assertTrue(self.run_join()['local_programmes_ready'])
    def test_missing_mtp_not_hidden_by_2654_backbone_nodes(self):
        self.catalogue['source_SU_nodes'][0]['scope']=0
        r=self.run_join();self.assertIn('missing_literal_MTP_continuation_operations',self.reasons(r))
        self.assertEqual(r['compiled_rank_programmes'],[])
    def test_relabelled_unknown_node_is_not_a_source_binding(self):
        self.manifest['rank_programmes'][0]['source_operations']['native_job'][0]['node']='invented.I0'
        r=self.run_join();self.assertIn('invalid_native_rank_programme',self.reasons(r))
    def test_stale_template_does_not_reuse_old_proof(self):
        self.manifest['rank_programmes'][0]['source_operations']['native_job'][0]['template_sha256']='0'*64
        self.assertFalse(self.run_join()['local_programmes_ready'])
    def test_parent_reservation_is_not_elaborated_leaf(self):
        self.manifest['rank_programmes'][0]['su_instance']='sp_su_s'
        self.assertFalse(self.run_join()['local_programmes_ready'])
    def test_provider_home_does_not_supply_su_home(self):
        self.manifest['rank_programmes'][0]['provider_home']=0
        self.assertFalse(self.run_join()['local_programmes_ready'])
    def test_wrong_die_engine_home_rejected(self):
        b=copy.deepcopy(self.binding);b['jobs']['native_job']['physical_instance']='su1'
        self.manifest['rank_programmes'][0]['binding']=self.pin('wrongdie.json',b)
        self.assertFalse(self.run_join()['local_programmes_ready'])
    def test_unchanged_template_with_changed_native_age_rejected(self):
        b=copy.deepcopy(self.binding);b['jobs']['native_job']['duration_cycles']=11
        self.manifest['rank_programmes'][0]['binding']=self.pin('wrongage.json',b)
        r=self.run_join();self.assertIn('native_calendar_rejected',self.reasons(r))
    def test_missing_rank_rejects_partial_dispatch(self):
        self.manifest['rank_programmes'].pop()
        r=self.run_join();self.assertIn('missing_rank_programme',self.reasons(r));self.assertEqual(r['compiled_rank_programmes'],[])
    def test_fusion_requires_rounding_order_proof(self):
        self.manifest['rank_programmes'][0]['source_operations']['native_job'].append(dict(node='stage1.I0',template_sha256='1'*64))
        self.assertFalse(self.run_join()['local_programmes_ready'])
    def test_duplicate_source_execution_rejected(self):
        self.manifest['rank_programmes'][4]['source_operations']['native_job'][0]['node']='mtp.I0'
        r=self.run_join();self.assertIn('invalid_native_rank_programme',self.reasons(r))
    def test_fabricated_operation_stage_is_rejected(self):
        self.inventory['source_operation_homes'][0]['stage']=1
        self.manifest['native_instance_inventory']=self.pin('inventory.json',self.inventory)
        self.assertFalse(self.run_join()['local_programmes_ready'])
    def test_mutated_elaboration_source_rejected(self):
        (self.root/'native.sv').write_text('// changed source\n')
        self.assertFalse(self.run_join()['local_programmes_ready'])

if __name__=='__main__':unittest.main()
