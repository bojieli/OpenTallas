from pathlib import Path
import sys,unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import deepseek_hbm_complete_index_ports as I

class IndexPorts(unittest.TestCase):
    def test_packed_word_recipe_matches_byte_recipe_all_codes(self):
        r=np.random.default_rng(68)
        for n in [1,31,32,33,64]:
            rows=r.integers(0,256,(n,68),dtype=np.uint8)
            rows[:,64:]=r.choice(np.array([1,2,126,127,251,252],np.uint8),(n,4))
            a,b,m=I.unpack(rows);x,y,_=I.R1.unpack(rows)
            self.assertTrue(np.array_equal(a,x));self.assertTrue(np.array_equal(b,y))
            self.assertGreater(m.counts['SHR'],0)
    def test_complete_RF_capacity_mapping_unique_copies(self):
        words=set()
        for partition in range(4):
            for warp in range(8):
                for reg in range(32):
                    for lane in range(32):
                        a=I.rf_location(partition,warp,reg,lane)
                        words.add((a['lane_group8'],a['subword'],a['depth_bank'],a['row']))
                        self.assertEqual(a['read_copies'],[0,1])
        self.assertEqual(len(words),32768)
        with self.assertRaises(ValueError):I.rf_location(4,0,0,0)
    def test_shared_raw_scales_units_nonoverlap_and_banks(self):
        words={I.shared_address(f'word{j}',r) for j in range(17) for r in range(64)}
        units={I.shared_address(f'unit{j}',r) for j in range(128) for r in range(64)}
        scales={I.shared_address(f'exp{j}',r) for j in range(4) for r in range(64)}
        self.assertFalse(words&units or words&scales or units&scales)
        self.assertEqual(I.END,55040);self.assertLess(I.END,65536)
        for name in ['word16','unit127','exp3']:
            for start in [0,32]:self.assertEqual(len({I.shared_address(name,start+l)//4%32 for l in range(32)}),32)
    def test_event_sources_register_lifetimes_and_failclosed_cost(self):
        c=I.events(partition=3,warp_slot=7,tile_row=32,active_lanes=31)
        self.assertLessEqual(c['RF_peak_value_registers']+8,32)
        regs={};visible=set()
        for e in c['events']:
            self.assertTrue(all(dep in visible for dep in e['dependencies']))
            for operand in e['operands']:
                if operand['kind']=='register':self.assertEqual(regs[operand['reg']],operand['producer_event'])
            if e['destination_register'] is not None:regs[e['destination_register']]=e['id']
            visible.add(e['id'])
            if e['shared']:self.assertTrue(e['shared']['one_word_per_bank'])
            self.assertIsNone(e['actual_hardware_timestamp'])
        self.assertIn('SHR',c['unbound_opcode_counts']);self.assertIsNone(c['qualified_cycles'])
        self.assertEqual(c['physical_admission'],'FAIL_CLOSED')
        with self.assertRaises(ValueError):I.events(tile_row=1)
    def test_refill_scatter_source_bytes_cover_exact_produced_rows(self):
        for start in [0,7,1023]:
            c=I.refill_events(95,start,64,256)
            ranges=[tuple(e['wire_byte_range']) for e in c['scatter_events']]
            expected=[(256+start*68+off,256+start*68+off+4) for off in range(0,64*68,4)]
            self.assertEqual(ranges,expected);self.assertEqual(len(c['scatter_events']),1088)
            for e in c['scatter_events']:
                for request in e['requires_return_requests']:
                    r=c['requests'][request];self.assertLessEqual(r['length_sectors'],16)
                self.assertIsNone(e['actual_hardware_timestamp'])
            self.assertIsNone(c['scatter_cycles']);self.assertEqual(c['staging_write_bytes'],4352)

if __name__=='__main__':unittest.main()
