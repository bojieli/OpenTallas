import importlib.util
import json
import random
import unittest
from pathlib import Path

P = Path(__file__).resolve().parents[1]/'tools/dsrom_finite_vm_calendar.py'
s = importlib.util.spec_from_file_location('finite_vm',P)
m = importlib.util.module_from_spec(s); s.loader.exec_module(m)

class FiniteVM(unittest.TestCase):
    def test_4096_selected_no_small_backend(self):
        x=m.build(); b=x['selected_backend']
        self.assertEqual((b['macros'],b['bits'],b['DEPTH_GROUPS']), (256,16777216,16))
        self.assertAlmostEqual(b['macro_body_mm2'],1.3236867072)
        self.assertFalse(x['admission']['parent_PnR'])
        self.assertEqual(x['calendar']['winner_compare_edges'],175528)
        self.assertEqual(x['calendar']['fill_upper_edges'],177641)

    def test_read_old_and_source_winner(self):
        x=m.calendar({3:10}, [('r',3)], [('field',3,20),('QE',3,30)])
        self.assertEqual(x['replies']['r'],10)
        self.assertEqual(x['image'][3],30)
        self.assertEqual(x['receipts']['field']['kind'],'SUPERSEDED_NOT_VISIBLE')
        self.assertEqual(x['receipts']['QE']['at'],9)
        self.assertLess(x['read_events'][0]['reply_capture'],x['write_events'][0]['issue'])

    def test_mask_packets_preserve_unwritten_lanes(self):
        old={i:100+i for i in range(64)}
        x=m.calendar(old,[], [('a',3,7),('b',19,8),('c',3,9)])
        native=dict(old)
        for e in x['write_events']:
            for lane,value in e['lanes'].items():
                self.assertTrue(e['lane_mask'] & (1<<lane))
                native[e['word']*16+lane]=value
        self.assertEqual(native,x['image'])
        self.assertEqual(native[2],102)
        self.assertEqual(x['receipts']['a']['kind'],'SUPERSEDED_NOT_VISIBLE')

    def test_random_alias_and_bank_calendar_matches_source(self):
        rng=random.Random(6144)
        for _ in range(30):
            mem={i:rng.randrange(1<<32) for i in range(128)}
            reads=[('r'+str(i),rng.randrange(128)) for i in range(23)]
            writes=[('w'+str(i),rng.randrange(128),rng.randrange(1<<32)) for i in range(47)]
            x=m.calendar(mem,reads,writes)
            expected=m.reference().ordered_edge(mem,reads,writes)
            self.assertEqual((x['replies'],x['image']),expected[:2])
            pairs=[(e['issue'],e['bank']) for e in x['write_events']]
            self.assertEqual(len(pairs),len(set(pairs)))
            self.assertEqual(len(x['receipts']),len(writes))
            self.assertLessEqual(x['busy_edges'],len(reads)+4+len(writes)+3)

    def test_worst_same_bank_full_frame_has_positive_bound(self):
        reads=[(i,i) for i in range(1520)]
        writes=[(i,i*64,i) for i in range(593)]
        x=m.calendar({i:0 for i in range(1520)},reads,writes)
        self.assertEqual(len(x['write_events']),593)
        self.assertEqual(x['busy_edges'],2120)
        self.assertEqual({e['bank'] for e in x['write_events']},{0})
        self.assertEqual(len(x['replies']),1520)
        self.assertEqual(len(x['receipts']),593)
        self.assertEqual(x['winner_compare_edges'],175528)
        self.assertEqual(x['fill_edges'],177641)

    def test_four_banks_no_free_arbitrary_read_ports(self):
        x=m.calendar({i:i for i in range(64)},[(i,i) for i in [0,17,34,51]],[(i,i,1) for i in [0,16,32,48]])
        self.assertEqual([e['issue'] for e in x['read_events']],[0,1,2,3])
        self.assertEqual([e['issue'] for e in x['write_events']],[8,9,10,11])

    def test_top_address_native_read_no_out_of_bounds_window(self):
        last=(1<<19)-1
        x=m.calendar({last:9}, [('r',last)],[])
        e=x['read_events'][0]
        self.assertEqual(e['base_word'],32764)
        self.assertEqual(m.word_home(last),dict(word=32767,bank=3,group=15,row=511,lane=15))

    def test_duplicate_reads_are_not_dropped(self):
        with self.assertRaises(ValueError): m.calendar({0:0}, [('r',0),('r',0)],[])
        x=m.calendar({0:2}, [('r0',0),('r1',0)],[])
        self.assertEqual(len(x['replies']),2)

    def test_capacity_refusal_before_acceptance(self):
        with self.assertRaises(ValueError): m.calendar({},[(i,0) for i in range(1521)],[])
        with self.assertRaises(ValueError): m.calendar({},[],[(i,0,0) for i in range(594)])

    def test_raw_width_epoch_address_contract(self):
        for value in [True,-1,1<<32,1.0]:
            with self.assertRaises(ValueError): m.calendar({},[],[('w',0,value)])
        for epoch in [True,-1,1<<32]:
            with self.assertRaises(ValueError): m.calendar({},[],[],epoch)
        for addr in [True,-1,1<<19]:
            with self.assertRaises(ValueError): m.word_home(addr)

    def test_credits_not_acceptance_or_idle_and_stale_reset(self):
        x=m.calendar({0:1}, [('r',0)], [('w',0,2)],epoch=7)
        l=m.FrameLease(x,7)
        with self.assertRaises(ValueError): l.rearm(True)
        with self.assertRaises(ValueError): l.receipt('read','r',6,4)
        with self.assertRaises(ValueError): l.receipt('write','w',7,7)
        l.receipt('read','r',7,4)
        l.receipt('write','w',7,8)
        with self.assertRaises(ValueError): l.rearm(False)
        l.rearm(True)
        with self.assertRaises(ValueError): l.receipt('write','w',7,8)

    def test_consumer_stall_does_not_remove_reply_seats(self):
        x=m.calendar({0:1},[(0,0)],[])
        l=m.FrameLease(x,0)
        self.assertEqual(x['backend_last_capture'],4)
        self.assertEqual(l.reads,{0:4})
        with self.assertRaises(ValueError): l.rearm(True)

    def test_HBM_inventory_not_gateway_only(self):
        clocks=m.build()['HBM_owner_join']['clock_inventory']
        self.assertEqual(clocks['DeepSeek']['retained_matrix_memory_macro_endpoints_per_SM'],104)
        self.assertEqual(clocks['DeepSeek']['retained_compute_macro_endpoints_per_SM'],64)
        self.assertEqual(clocks['DeepSeek']['gateway_service_macro_endpoints_per_SM'],138)
        self.assertFalse(m.build()['HBM_owner_join']['qualification'])

    def test_model_replay(self):
        retained=json.loads((m.BASE/'model.json').read_text())
        self.assertEqual(retained,m.build())

if __name__=='__main__': unittest.main()
