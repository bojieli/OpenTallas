import copy
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('reservations', Path(__file__).resolve().parents[1]/'static_vm_reservations.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

class FixedScheduleTests(unittest.TestCase):
    def setUp(self):
        self.contract = dict(stream_period_ps=3, vm_period_ps=4, stream_phase_ps=0, vm_phase_ps=0,
            banks=32, bank_ops_per_cycle=1, read_ingress_per_cycle=1, write_ingress_per_cycle=1,
            request_min_ps=1, read_min_ps=5, commit_min_ps=2,
            slot_capacity={'su/write/0':1, 'su/read/0':1, 'su/read/1':1},
            client_capacity={'su':3}, measured_native_bounds=True)
        self.schedule = dict(trace_complete=True, events=[
            dict(id='w',kind='write',client='su',slot=0,row=64,tag=0,issue_cycle=0,
                 ingress_cycle=1,service_cycle=2,commit_cycle=4,deadline_cycle=4),
            dict(id='r',kind='read',client='su',slot=0,row=64,tag=1,issue_cycle=4,
                 ingress_cycle=4,service_cycle=5,response_cycle=9,deadline_cycle=9)],
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
            ingress_cycle=5,service_cycle=6,response_cycle=10,deadline_cycle=10)
        self.schedule['events'].append(other)
        self.assertIn('slot_overflow',self.kinds())
    def test_native_group_split(self):
        other=copy.deepcopy(self.schedule['events'][1]); other.update(id='r2',slot=1,row=65,
            issue_cycle=5,ingress_cycle=5,service_cycle=6,response_cycle=10,deadline_cycle=10)
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
    def test_missing_producer_done_is_not_qualified(self):
        self.schedule["jobs"] = self.schedule["jobs"][1:]
        self.assertIn("missing_producer_done",self.kinds())
    def test_invalid_capacity_is_rejected(self):
        self.contract["banks"]=0
        self.assertIn("invalid_contract",self.kinds())
    def test_issue_only_trace_does_not_prove_reservations(self):
        del self.schedule['events'][1]['service_cycle']
        self.assertIn('missing_reservation',self.kinds())

if __name__ == '__main__': unittest.main()
