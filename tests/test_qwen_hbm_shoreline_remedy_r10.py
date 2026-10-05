import sys,unittest
from pathlib import Path
from fractions import Fraction as F
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from qwen_hbm_shoreline_remedy_r10 import Provider,reserves,geometry,composed,comparisons,SERIAL,FAST,edge,audit_bank_events,source_timing
from qwen_hbm_downstream_contract_r8 import fixture

class ShorelineTests(unittest.TestCase):
    def setUp(self):self.rows=fixture()['sector_rows']
    def test_geometry_remedy_retains_resources_and_prices_reserves(self):
        g=geometry();r=reserves();self.assertTrue(g['geometry_fit']);self.assertEqual(g['geometry_conflicts'],[])
        self.assertEqual(g['SMs_per_die'],32);self.assertEqual(g['PCs_per_stack'],32);self.assertEqual(g['outline_area_mm2'],815)
        self.assertGreaterEqual(g['selected_slot_mm2_per_stack'],r['minimum_slot_mm2_per_stack'])
        self.assertGreater(g['selected_depth_um'],900);self.assertGreater(r['exclusive_projection_alternative_slot_mm2_per_stack'],80)
        self.assertEqual(r['signal_share'],.5);self.assertGreater(r['PDN_exclusive_projection_fraction'],.8)
        self.assertGreater(r['clock']['area_mm2'],1);self.assertGreater(r['via_area_mm2'],0)
        self.assertLess(r['PHY_candidate_total_signal_pins'],r['PHY_50percent_edge_pin_capacity'])
    def test_parent_bound_Qwen_scope_and_alternatives(self):
        x=comparisons();self.assertAlmostEqual(x['Qwen']['base_system_shortfall_mm2'],10.5320509472)
        self.assertIsNone(x['DeepSeek']['required_service_mm2_per_stack']);self.assertFalse(x['DeepSeek']['qualification_transfer'])
        self.assertFalse(x['remedies'][1]['width_only_inside_outline']);self.assertFalse(x['remedies'][2]['within_source_reticle'])
        self.assertTrue(x['zero_PHY_replacement_credit'])
    def test_actual_completion_absence_and_numeric_admission(self):
        x=composed();self.assertEqual(x['source_input_events'],[]);self.assertFalse(x['RTL_admission']);self.assertFalse(x['provider_PASS'])
        self.assertEqual(x['exact_arithmetic_admission']['parent_commit'],'b33395215')
        self.assertFalse(x['exact_arithmetic_admission']['qualification_transfer'])
    def test_four_credit_backpressure_not_whole_opcode(self):
        p=Provider(self.rows)
        for i in range(4):self.assertTrue(p.reserve(i,7,8))
        self.assertFalse(p.reserve(4,7,8));p.advance(1000000)
        self.assertEqual(len(p.live),4);self.assertEqual(len(p.completed),0)
        self.assertTrue(p.opcode_issue(10,0,1,7,8))
        with self.assertRaises(ValueError):p.opcode_complete(10,0,1)
        with self.assertRaises(ValueError):p.WR_column(0,(self.rows[0]['sector'],7,8))
    def test_full_AW_RAW_delayed_visible_and_held_cancel(self):
        # Full AW identity fixture; no low-address alias or payload transfer.
        rows=[dict(sector=0,partial=False),dict(sector=1<<32,partial=False)]
        p=Provider(rows);p.reserve(0,7,8);p.reserve(1,7,8)
        a=(0,7,8);b=(1<<32,7,8);due=p.WR_column(0,a)
        self.assertFalse(p.RAW_read_ready(0));self.assertFalse(p.RAW_read_ready(1<<32))
        with self.assertRaises(ValueError):p.ACK_capture(0,a)
        p.advance(due);self.assertTrue(p.RAW_read_ready(0));self.assertFalse(p.RAW_read_ready(1<<32));self.assertEqual(p.backing[0],(0,7,8));self.assertNotIn(1<<32,p.backing)
        p.ACK_capture(0,a);held=p.live[0]['held'];p.cancel(0,a);self.assertEqual(p.live[0]['held'],held)
        with self.assertRaises(ValueError):p.reverse_credit(0,a)
        p.advance(p.live[0]['ACK_landing']);p.sector_store(0,a)
        p.advance(p.live[0]['store_due']+SERIAL);p.sector_retire(0,a)
        p.advance(p.live[0]['reverse_due']);p.reverse_credit(0,a)
        self.assertEqual(p.completed,set());self.assertEqual(p.cancelled,{0})
    def test_inflight_RMW_cancel_must_drain_owned_return(self):
        p=Provider(self.rows);p.reserve(0,7,8);owner=(self.rows[0]['sector'],7,8)
        due=p.RMW_read(0,owner);p.cancel(0,owner)
        with self.assertRaises(ValueError):p.reverse_credit(0,owner)
        with self.assertRaises(ValueError):p.cancel_read_drain(0,owner)
        p.advance(due);self.assertIn(0,p.live);p.cancel_read_drain(0,owner)
        p.advance(p.live[0]['reverse_due']);p.reverse_credit(0,owner);self.assertEqual(p.cancelled,{0})
    def test_PC_command_FIFO_finite_and_current_refresh(self):
        p=Provider(self.rows)
        for i in range(4):p.reserve(i,7,8)
        for i in range(3):self.assertIsNot(p.RMW_read(i,(self.rows[i]['sector'],7,8)),False)
        self.assertIs(p.RMW_read(3,(self.rows[3]['sector'],7,8)),False)
        p.advance(4000000)
        self.assertTrue(any(e['kind']=='current_REFRESH' for e in p.log))
        self.assertEqual(p.peak['command_slots_per_PC'],3)
        audit_bank_events(p.cal.events,source_timing())
    def test_four_reader_owners_hold_through_cancel_and_exact_discard(self):
        # Explicit synthetic state at reader stage; no actual lease generated.
        p=Provider(self.rows);p.generation=(7,8);p.lease=(7,8)
        rows=fixture()['KV_prefix_read_rows']
        for i in range(4):
            owner=(rows[i]['sector'],7,8)
            if not p.reader_accept(i,*owner):
                p.advance(min(x for pc in p.pending_commands for x in pc if x>p.now))
                self.assertTrue(p.reader_accept(i,*owner))
        self.assertFalse(p.reader_accept(4,rows[4]['sector'],7,8))
        p.opcode_inputs[13]=(3,13,7,8);p.opcode_inputs[15]=(5,15,7,8)
        p.lease_cancel(7,8)
        with self.assertRaises(ValueError):p.lease_cancel_release(7,8,[])
        for i in range(4):
            owner=(rows[i]['sector'],7,8)
            p.advance(max(p.now,p.readers[i]['ready']));p.reader_cancel_discard(i,owner)
            self.assertIn(i,p.readers)
            p.advance(p.readers[i]['reverse_due']);p.reader_reverse_credit(i,owner)
        self.assertEqual(len(p.reader_cancelled),4);self.assertEqual(len(p.reader_done),0)
        with self.assertRaises(ValueError):p.lease_cancel_release(7,8,[(13,3,13,9,8),(15,5,15,7,8)])
        p.lease_cancel_release(7,8,[(13,3,13,7,8),(15,5,15,7,8)])
        self.assertIsNone(p.lease)
    def test_272_writer_288_reader_explicit_synthetic_protocol_inputs(self):
        # Protocol fixture ONLY. Inputs below are explicitly injected; none
        # are source observations or callbacks generated by elapsed bounds.
        p=Provider(self.rows);p.reserve(0,7,8);p.opcode_issue(10,0,1,7,8)
        for i,r in enumerate(self.rows):
            if i:p.reserve(i,7,8)
            owner=(r['sector'],7,8)
            if r['partial']:
                due=p.RMW_read(i,owner);p.advance(due)
                self.assertEqual(p.live[i]['phase'],'RMW_result_wait')
                p.RMW_result_commit(i,owner)
                with self.assertRaises(ValueError):p.WR_column(i,owner)
                p.RMW_owned_retire(i,owner)
            due=p.WR_column(i,owner);p.advance(due);p.ACK_capture(i,owner)
            p.advance(p.live[i]['ACK_landing']);p.sector_store(i,owner)
            p.advance(p.live[i]['store_due']+SERIAL);p.sector_retire(i,owner)
            p.advance(p.live[i]['reverse_due']);p.reverse_credit(i,owner)
        self.assertEqual(len(p.completed),272)
        p.advance(edge(p.now,SERIAL));p.opcode_complete(10,0,1);p.advance(p.now+SERIAL);p.IRS_retire(10,0,1)
        p.opcode_issue(11,1,2,7,8);p.opcode_complete(11,1,2);p.advance(p.now+SERIAL);p.IRS_retire(11,1,2)
        with self.assertRaises(ValueError):p.acquire(7,8,False)
        p.acquire(7,8,dict(position=0,producer=7,transport=8,sector_retire_quorum=272,scope='SYNTHETIC_TEST_INPUT')); p.opcode_issue(12,2,3,7,8)
        for i,r in enumerate(fixture()['KV_prefix_read_rows']):
            owner=(r['sector'],7,8);self.assertTrue(p.reader_accept(i,*owner))
            p.advance(p.readers[i]['ready']);p.reader_result(i,owner);p.reader_retire(i,owner)
            self.assertIn(i,p.readers)
            p.advance(p.readers[i]['reverse_due']);p.reader_reverse_credit(i,owner)
        self.assertEqual(len(p.reader_done),288)
        p.advance(edge(p.now,SERIAL));p.opcode_complete(12,2,3);p.advance(p.now+SERIAL);p.IRS_retire(12,2,3)
        with self.assertRaises(ValueError):p.release(7,8)
        for instruction in (13,14,15):
            p.opcode_issue(instruction,instruction-10,instruction,7,8)
            p.opcode_result_commit(instruction,7,8);p.opcode_complete(instruction,instruction-10,instruction)
            with self.assertRaises(ValueError):p.IRS_retire(instruction,instruction-10,instruction)
            p.advance(p.now+SERIAL);p.IRS_retire(instruction,instruction-10,instruction)
        p.release(7,8);p.writer_context_release();self.assertIsNone(p.lease)
        audit_bank_events(p.cal.events,source_timing())

if __name__=='__main__':unittest.main()
