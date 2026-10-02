import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from qwen_hbm_inventory_timers_r9 import Countdown,modular_due,timers,inventory,graph,compose,SectorStorePipe,ReaderWindow,command_prefix
from qwen_hbm_downstream_contract_r8 import fixture

class InventoryTimersTests(unittest.TestCase):
    def test_source_inventory_and_no_replacement(self):
        x=inventory();self.assertFalse(x['actual_floorplan_source_hashes_match']);self.assertEqual(set(x['source_hash_mismatches']),{'tools/uarch_model.py'})
        self.assertEqual(x['inherited_replacement_credit_mm2'],0)
        self.assertTrue(all(r['replacement_credit_mm2']==0 for r in x['named_components']))
        self.assertEqual(x['PHY_min_period_ps'],1000)
    def test_every_deadline_expires_even_during_unbounded_hold(self):
        x=timers()
        for row in x['constraints']:
            n=row['max_edges'];c=Countdown(n);c.arm(n)
            for _ in range(n):self.assertFalse(c.ready);c.edge()
            self.assertTrue(c.ready)
            for _ in range(2**15+1):c.edge()
            self.assertTrue(c.ready)
            with self.assertRaises(ValueError):c.arm(n+1)
        self.assertEqual(x['max_retained_local_deadline_edges'],9214)
        self.assertEqual(x['modular_counter_bits_if_expiring'],15)
        self.assertFalse(x['applied_width_reduction'])
    def test_wrap_comparison_and_reject_half_range_mutant(self):
        bits=15;mask=(1<<bits)-1
        for row in timers()['constraints']:
            d=row['max_edges']
            for start in (0,mask-1,mask-d//2):
                deadline=(start+d)&mask
                for delta in (0,d-1,d,d+1):
                    self.assertEqual(modular_due((start+delta)&mask,deadline,bits,abs(delta-d)),delta>=d)
        with self.assertRaises(ValueError):modular_due(0,0,15,1<<14)
        # An owner may stall longer than half-range; no timer proves its release.
        with self.assertRaises(ValueError):modular_due(1,0,15,1<<15)
    def test_max_reload_cannot_shorten_hazard(self):
        c=Countdown(420);c.arm(420);c.edge();c.arm(12);self.assertEqual(c.left,419)
    def test_no_timer_lever_can_close_slot(self):
        c=compose();a=c['resource_area']
        self.assertGreater(a['impossible_free_timer_overflow_mm2_per_stack'],1)
        self.assertGreater(a['conditional_countdown_overflow_mm2_per_stack'],1)
        self.assertEqual(a['applied_replacement_credit_mm2'],0)
        self.assertEqual(a['routing_signal_escrow'],.5)
        self.assertEqual(a['via_count_per_stack'],60352)
        self.assertFalse(c['RTL_admission']);self.assertFalse(a['fit'])
    def test_exact_metadata_graph_no_completions_from_bounds(self):
        x=graph();f=fixture()
        self.assertEqual(len(x['reader_events']),288)
        self.assertEqual(len(x['publication_dependencies']),272)
        self.assertEqual(x['RMW_sectors'],256)
        self.assertEqual([r['sector'] for r in x['reader_events']],[r['sector'] for r in f['KV_prefix_read_rows']])
        self.assertEqual(x['actual_input_events'],[])
        self.assertEqual(x['blocked_without_inputs']['reader_acceptances'],0)
        self.assertEqual(x['PV_dependencies'],[12,14])
    def test_finite_reservations_do_not_release_on_store_or_retire(self):
        rows=fixture()['sector_rows'];p=SectorStorePipe(rows)
        for r in rows[:4]:self.assertTrue(p.reserve(r['ordinal'],r['sector'],7,8))
        r=rows[4];self.assertFalse(p.reserve(4,r['sector'],7,8))
        for _ in range(100):self.assertIsNone(p.edge(True))
        self.assertEqual(len(p.live),4)
        with self.assertRaises(ValueError):p.reverse_credit(0,(rows[0]['sector'],7,8))
        p.store_visible(0,(rows[0]['sector'],7,8));self.assertIsNone(p.edge(True))
        held=p.held
        for _ in range(100):self.assertIsNone(p.edge(False));self.assertEqual(p.held,held)
        self.assertEqual(p.edge(True),held);self.assertEqual(len(p.live),4)
        with self.assertRaises(ValueError):p.reverse_credit(0,(rows[0]['sector'],9,8))
        p.reverse_credit(0,held[1]);self.assertTrue(p.reserve(4,r['sector'],7,8))
    def test_causal_source_address_prefix_no_provider_credit(self):
        x=command_prefix()
        self.assertEqual(len(x['commands']),8)
        self.assertEqual(x['command_timing_audit']['status'],'PASS_COMMAND_TIMING_INEQUALITIES')
        self.assertEqual(x['held_sector_owners'],4)
        self.assertEqual(x['blocked_reader_sectors'],288)
        self.assertEqual(x['retirement_events'],0)
        self.assertEqual(x['WR_commands'],0)
        self.assertTrue(all(e['ps']==e['observe_ps'] for e in x['modeled_service_events']))
    def test_reader_288_finite_inputs_and_no_take_retirement(self):
        rows=fixture()['KV_prefix_read_rows'];p=ReaderWindow(rows)
        with self.assertRaises(ValueError):p.acquire(False)
        with self.assertRaises(ValueError):p.reserve(0,rows[0]['sector'],7,8)
        p.acquire(True) # Synthetic protocol test lease, not source evidence.
        for batch in range(0,288,4):
            for i in range(batch,batch+4):
                owner=(rows[i]['sector'],7,8)
                self.assertTrue(p.reserve(i,*owner));p.take(i,owner,0)
            if batch+4<288:self.assertFalse(p.reserve(batch+4,rows[batch+4]['sector'],7,8))
            for i in range(batch,batch+4):
                with self.assertRaises(ValueError):p.retire(i,(rows[i]['sector'],9,8))
                p.retire(i,(rows[i]['sector'],7,8))
        self.assertEqual(len(p.done),288)
    def test_all272_synthetic_protocol_inputs_scope_only(self):
        # These test inputs assert store/credit events explicitly. They are not
        # source observations, cycle bounds, opcode retirement or lease ACKs.
        rows=fixture()['sector_rows'];p=SectorStorePipe(rows)
        for batch in range(0,272,4):
            for r in rows[batch:batch+4]:
                i=r['ordinal'];owner=(r['sector'],7,8)
                self.assertTrue(p.reserve(i,*owner));p.store_visible(i,owner)
            p.edge(False)
            for _ in range(3):held=p.held;p.edge(False);self.assertEqual(p.held,held)
            while p.held:
                event=p.edge(True);p.reverse_credit(*event)
        self.assertEqual(len(p.done),272);self.assertEqual(p.peak,4);self.assertEqual(p.live,{})

if __name__=='__main__':unittest.main()
