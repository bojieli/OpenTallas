import copy
import hashlib
import tempfile
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('reservations', Path(__file__).resolve().parents[1]/'static_vm_reservations.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

class FixedScheduleTests(unittest.TestCase):
    def setUp(self):
        self.contract = dict(stream_period_ps=3, vm_period_ps=4, stream_phase_ps=0, vm_phase_ps=0,
            banks=32, bank_queue_capacity=4, bank_ops_per_cycle=1, read_ingress_per_cycle=1, write_ingress_per_cycle=1,
            request_min_ps=1, read_min_ps=5, commit_min_ps=2,
            slot_capacity={'su/write/0':1, 'su/read/0':1, 'su/read/1':1},
            client_capacity={'su':3}, measured_native_bounds=True)
        self.schedule = dict(trace_complete=True, events=[
            dict(id='w',kind='write',client='su',slot=0,row=64,tag=0,issue_cycle=0,
                 ingress_cycle=1,bank_enqueue_cycle=1,service_cycle=2,commit_cycle=4,deadline_cycle=4),
            dict(id='r',kind='read',client='su',slot=0,row=64,tag=1,issue_cycle=4,
                 ingress_cycle=4,bank_enqueue_cycle=4,service_cycle=5,response_cycle=9,deadline_cycle=9)],
            jobs=[dict(client='su',tag=0,done_cycle=4),dict(client='su',tag=1,done_cycle=9)],
            dependencies=[dict(producer='w',consumer='r')])
    def kinds(self):
        return {x['kind'] for x in m.check(self.schedule,self.contract)['violations']}
    def test_exact_reservations_pass_without_rewriting(self):
        snapshot=copy.deepcopy(self.schedule)
        result=m.check(self.schedule,self.contract)
        self.assertEqual(result['status'],'pass'); self.assertFalse(result['qualified'])
        self.assertEqual(snapshot,self.schedule)
    def test_shared_single_port_read_write_collision(self):
        self.schedule['events'][1].update(service_cycle=2,ingress_cycle=2,issue_cycle=1,row=96)
        self.assertIn('bank_collision',self.kinds())
    def test_ingress_bottleneck_even_distinct_banks(self):
        other=copy.deepcopy(self.schedule['events'][1]); other.update(id='r2',slot=1,row=65)
        self.schedule['events'].append(other)
        self.assertIn('ingress_collision',self.kinds())
    def test_fixed_deadline_cannot_be_relaxed(self):
        self.schedule['events'][1]['response_cycle']=10
        self.assertIn('missed_fixed_deadline',self.kinds())
    def test_finite_slot_overflow(self):
        other=copy.deepcopy(self.schedule['events'][1]); other.update(id='r2',issue_cycle=5,
            ingress_cycle=5,bank_enqueue_cycle=5,service_cycle=6,response_cycle=10,deadline_cycle=10)
        self.schedule['events'].append(other)
        self.assertIn('slot_overflow',self.kinds())
    def test_native_group_split(self):
        other=copy.deepcopy(self.schedule['events'][1]); other.update(id='r2',slot=1,row=65,
            issue_cycle=5,ingress_cycle=5,bank_enqueue_cycle=5,service_cycle=6,response_cycle=10,deadline_cycle=10)
        self.schedule['events'].append(other);self.schedule['groups']=[dict(events=['r','r2'])]
        self.assertIn('response_group_split',self.kinds())
    def test_done_before_real_commit(self):
        self.schedule['jobs'][0]['done_cycle']=3
        self.assertIn('done_before_commit',self.kinds())
    def test_consume_before_commit(self):
        self.schedule['events'][1].update(service_cycle=2,ingress_cycle=2,issue_cycle=1)
        self.assertIn('consume_before_commit',self.kinds())
    def test_provisional_latencies_are_incomplete(self):
        self.contract['measured_native_bounds']=False
        self.assertEqual(m.check(self.schedule,self.contract)['status'],'incomplete')
    def test_qr_candidate_hash_is_explicit_and_bijective(self):
        contract=dict(self.contract,bank_mapping='xor_row7_5_shift2')
        mapped={(m.bank_of(row,contract),row>>5) for row in range(16384)}
        self.assertEqual(len(mapped),16384)
        qr=[32*(i//4)+28+i%4 for i in range(16)]
        self.assertEqual(len({m.bank_of(row,self.contract) for row in qr}),4)
        self.assertEqual(len({m.bank_of(row,contract) for row in qr}),16)
        for base in range(0,16384,16):
            self.assertEqual(len({m.bank_of(base+i,contract) for i in range(16)}),16)
    def test_independent_capture_and_control_ingress_ports(self):
        self.contract['ingress_capacities']={'ctrl_p3':1,'ctrl_p4':1,'capture0':1}
        self.schedule['events'][0]['ingress_resource']='ctrl_p4'
        self.schedule['events'][1]['ingress_resource']='ctrl_p3'
        extra=copy.deepcopy(self.schedule['events'][0]);extra.update(id='w2',slot=1,row=65,ingress_resource='capture0')
        self.contract['slot_capacity']['su/write/1']=1
        self.schedule['events'].append(extra)
        self.assertEqual(m.check(self.schedule,self.contract)['status'],'pass')
        extra['ingress_resource']='ctrl_p4'
        self.assertIn('ingress_collision',self.kinds())
    def test_missing_physical_ingress_resource_incomplete(self):
        self.contract['ingress_capacities']={'ctrl_p3':1,'ctrl_p4':1}
        self.assertEqual(m.check(self.schedule,self.contract)['status'],'incomplete')
    def test_bank_queue_bound_is_not_endpoint_bound(self):
        self.contract['bank_queue_capacity']=1
        first=self.schedule['events'][1]
        first.update(ingress_cycle=4,bank_enqueue_cycle=4,service_cycle=8,response_cycle=13,deadline_cycle=13)
        second=copy.deepcopy(first)
        second.update(id='r2',slot=1,issue_cycle=5,ingress_cycle=5,bank_enqueue_cycle=5,
                      service_cycle=9,response_cycle=14,deadline_cycle=14)
        self.schedule['events'].append(second)
        self.assertIn('bank_queue_overflow',self.kinds())
    def test_missing_bank_enqueue_remains_incomplete(self):
        del self.schedule['events'][0]['bank_enqueue_cycle']
        self.assertEqual(m.check(self.schedule,self.contract)['status'],'incomplete')
    def test_trace_start_and_done_rows_join_by_job(self):
        self.schedule['jobs'].insert(0,dict(client='su',tag=0,start_cycle=0))
        self.assertEqual(m.check(self.schedule,self.contract)['status'],'pass')
        self.schedule['events'][0]['job']=1
        self.schedule['jobs'][1].update(job=2)
        self.assertIn('missing_producer_done',self.kinds())
    def test_model_trace_without_native_edges_is_incomplete(self):
        for event in self.schedule['events']:
            del event['service_cycle']
            del event['ingress_cycle']
        self.assertEqual(m.check(self.schedule,self.contract)['status'],'incomplete')
    def test_unknown_bank_hash_rejected(self):
        self.contract['bank_mapping']='unimplemented'
        self.assertIn('invalid_contract',self.kinds())
    def test_missing_producer_done_is_not_qualified(self):
        self.schedule["jobs"] = self.schedule["jobs"][1:]
        self.assertIn("missing_producer_done",self.kinds())
    def test_invalid_capacity_is_rejected(self):
        self.contract["banks"]=0
        self.assertIn("invalid_contract",self.kinds())
    def test_issue_only_trace_does_not_prove_reservations(self):
        del self.schedule['events'][1]['service_cycle']
        self.assertIn('missing_reservation',self.kinds())

class ActualOneReadOneWriteTests(unittest.TestCase):
    def setUp(self):
        FixedScheduleTests.setUp(self)
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        source=self.root/'bank.sv';source.write_text('// compiler test source pin; hardware qualification is separate\n')
        self.contract.update(bank_port_capacities={'read':1,'write':1},same_address_policy='forbid',
                             bank_port_evidence=[dict(path='bank.sv',sha256=hashlib.sha256(source.read_bytes()).hexdigest())])
        self.schedule['events'][1].update(issue_cycle=0,ingress_cycle=1,bank_enqueue_cycle=1,
                                         service_cycle=2,row=96,response_cycle=5,deadline_cycle=5)
        self.schedule['dependencies']=[]
        self.schedule['jobs'][1]['done_cycle']=5

    def result(self):
        return m.check(self.schedule,self.contract,self.root)

    def kinds(self):
        return {x['kind'] for x in self.result()['violations']}

    def test_actual_independent_read_and_write_ports(self):
        before=copy.deepcopy(self.schedule)
        self.assertEqual(self.result()['status'],'pass')
        self.assertEqual(before,self.schedule)
        self.assertFalse(self.result()['qualified'])

    def test_two_reads_cannot_borrow_write_port(self):
        self.contract['read_ingress_per_cycle']=2
        other=copy.deepcopy(self.schedule['events'][1]);other.update(id='r2',slot=1,row=128)
        self.schedule['events'].append(other)
        self.assertIn('bank_port_collision',self.kinds())

    def test_two_writes_cannot_borrow_read_port(self):
        self.contract['write_ingress_per_cycle']=2;self.contract['slot_capacity']['su/write/1']=1
        other=copy.deepcopy(self.schedule['events'][0]);other.update(id='w2',slot=1,row=128)
        self.schedule['events'].append(other)
        self.assertIn('bank_port_collision',self.kinds())

    def test_same_address_requires_explicit_actual_visibility(self):
        self.schedule['events'][1]['row']=64
        self.assertIn('same_edge_read_write_address_collision',self.kinds())
        self.contract['same_address_policy']='read_before_write'
        self.assertIn('same_edge_read_visibility_unbound',self.kinds())
        self.schedule['events'][1]['read_visibility']='before_same_edge_write'
        self.assertEqual(self.result()['status'],'pass')

    def test_read_before_write_cannot_supply_new_value_dependency(self):
        self.schedule['events'][1].update(row=64,read_visibility='before_same_edge_write')
        self.contract['same_address_policy']='read_before_write'
        self.schedule['dependencies']=[dict(producer='w',consumer='r')]
        self.assertIn('consume_before_commit',self.kinds())

    def test_profile_cannot_inflate_ports(self):
        self.contract['bank_port_capacities']['read']=2
        self.assertIn('invalid_contract',self.kinds())

    def test_changed_source_cannot_qualify_new_profile(self):
        (self.root/'bank.sv').write_text('different actual bank')
        self.assertIn('invalid_contract',self.kinds())

    def test_group_response_deadline_stays_fixed_with_1r1w(self):
        self.contract['read_ingress_per_cycle']=2
        other=copy.deepcopy(self.schedule['events'][1]);other.update(id='r2',slot=1,row=97,
            response_cycle=6,deadline_cycle=6)
        self.schedule['events'].append(other);self.schedule['groups']=[dict(events=['r','r2'])]
        self.assertIn('response_group_split',self.kinds())

if __name__ == '__main__': unittest.main()
