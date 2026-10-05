"""Diagnostic nonperturbation and valid overlapping wait accounting."""
import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import uarch_model_qwen_kv_stall_attribution as D

class AttributionTests(unittest.TestCase):
    def test_native_pc_deadline_and_event_digest_unchanged(self):
        a=D.PCService();b=D.TracedPC()
        for layer,st,sector,write,at in [(0,0,0,False,0),(0,0,0,True,0),(0,0,0,False,0),(0,0,4,False,0),(0,0,131072,False,5000000),(1,0,0,False,5001000)]:
            answer=b.column(layer,st,sector,write,at)
            self.assertEqual(a.column(layer,st,sector,write,at),answer)
            self.assertEqual(sum(b.last_parts.values()),int(answer/1000)-D.math.ceil(at/1000))
        self.assertEqual(a.digest.hexdigest(),b.digest.hexdigest())
        self.assertEqual(a.count,b.count);self.assertEqual(a.states,b.states)

    def test_queue_backlog_is_separate_from_feedback_latency(self):
        b=D.TracedPC();b.column(0,0,0,False,10000000)
        b.column(0,0,1,False,0)
        self.assertGreater(b.last_parts['older_PC_reserved_work'],9000)
        self.assertLessEqual(b.last_parts['PC_command_feedback_II5'],5)

    def test_one_layer_every_frozen_reservation_digest_and_credit_unchanged(self):
        old=json.loads((D.ROOT/'results/uarch/qwen_rom_kv_credit_allocator_20261002/model-r4.json').read_text())['calendar']['rows'][0]
        row=D.traced_calendar(0,0,D.Fraction(451*2500,3),D.TracedPC())
        self.assertEqual(float(row.pop('end_ps')),old['all_grants_ps'])
        self.assertEqual(float(row.pop('fill_end_ps')),old['fill_ready_ps'])
        diag=row.pop('diagnostic')
        for key,value in row.items():self.assertEqual(json.loads(json.dumps(value)),old[key])
        self.assertLessEqual(diag['fixed_lease_group16_span_lower_ps'],old['all_grants_ps'])
        self.assertLessEqual(diag['fixed_lease_global128_span_lower_ps'],old['all_grants_ps'])
        self.assertTrue(diag['allocator_exclusive_wait_ps'])

    def test_lower_bound_serializer_and_owner_payload_dual_receipts(self):
        rows=[dict(diagnostic=dict(owner_group_slots_per_stack=[[8192]*8 for _ in range(4)])) for _ in range(36)]
        b=D.lower_bounds(dict(rows=rows,controller=dict(commands_per_shared_path=[[1]*4 for _ in range(4)])))
        self.assertAlmostEqual(b['owner_DATA_plus_GRANT_port_s'],0.000294912)
        self.assertLess(b['column_payload_only_port_s'],b['owner_DATA_plus_GRANT_port_s'])
        self.assertTrue(b['bounds_overlap_not_sum'])

    def test_mixed_resource_blocks_are_one_wall_interval(self):
        class Head:head=('K',0,16)
        diag=D.Diagnostic()
        diag.allocator_wait(0,100,[0],[Head()],[0],0,D.Counter({(0,0):64}),D.Counter(),0,0,0)
        self.assertEqual(sum(diag.wait.values()),100)
        self.assertEqual(len(diag.wait),1)
        self.assertIn('global_cohort_credit',next(iter(diag.wait)))
        self.assertIn('group16_credit',next(iter(diag.wait)))

if __name__=='__main__':unittest.main()
