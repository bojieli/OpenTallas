from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import deepseek_hbm_complete_calendar as C
import deepseek_hbm_complete_canonical as K
import deepseek_hbm_complete_isa as I

class CompleteCalendar(unittest.TestCase):
    def test_all2213_cost_holes_nonzero_failclosed(self):
        x=C.build();self.assertEqual(x['whole_program_op_count'],2213)
        self.assertEqual(x['whole_program_physical_admission'],'FAIL_CLOSED')
        for o in x['operations']:
            self.assertIsNone(o['qualified_cycles']);self.assertTrue(o['missing_costs'])
            self.assertIsNone(o['shared_word_bank_map']);self.assertEqual(o['shared_bytes_per_fast_1p2GHz_cycle'],96)
        self.assertTrue(x['recipes']['INDEX32_BLOCK_ROUND']['one_warp_candidate']['RF32_fit'])
        self.assertIsNone(x['recipes']['EXP']['one_warp_candidate']['issue_cycles'])
    def test_scalar_div_one_lane_percycle_allready52(self):
        c=K.events(I.recipe('DIV'),32);r=next(e for e in c['events'] if e['opcode']=='DIV')
        self.assertEqual(len(r['scalar_issue_events']),32)
        issue=[e['issue_candidate'] for e in r['scalar_issue_events']]
        self.assertEqual(issue,list(range(issue[0],issue[0]+32)))
        self.assertTrue(all(e['active_lanes']==1 for e in r['scalar_issue_events']))
        self.assertEqual(r['dependent_vector_ready_candidate']-r['RF_read_candidate'],52)
    def test_preserves_legacy_recipes_and_rejects_free_INT(self):
        p=I.recipe('EXP');old=[dict(i) for i in p];c=K.events(p)
        self.assertEqual(p,old);self.assertFalse(c['physical_bank_service_and_SSFF_bound'])
        self.assertIn('F2I',c['unbound_opcode_counts']);self.assertIn('XOR',c['unbound_opcode_counts'])
        for e in c['events']:
            if e['opcode'] in ['IADD','FCMP_GT','FCMP_LT']:
                self.assertEqual(e['RF_writeback_candidate']-e['RF_read_candidate'],9)

if __name__=='__main__':unittest.main()
