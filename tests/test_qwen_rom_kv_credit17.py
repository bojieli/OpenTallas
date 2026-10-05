"""Finite68pending64RAM+4spill and one17credit calendar functional checks."""
import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import uarch_model_qwen_kv_credit17 as C

class Credit17Tests(unittest.TestCase):
    def test68_capacity_has_exact64_RAM4_spill_and_no_early_reuse(self):
        p=C.SpillPending();slots=[p.issue((i,0),i,9,13,0) for i in range(68)]
        self.assertEqual(sum(s['storage']=='RAM' for s in slots),64)
        self.assertEqual(sum(s['storage']=='FF_SPILL' for s in slots),4)
        with self.assertRaisesRegex(ValueError,'68'):p.issue((100,0),100,9,13,0)
        p.returned((67,0),67,9,13,25,b'a'*32)
        with self.assertRaisesRegex(ValueError,'68'):p.issue((100,0),100,9,13,26)
        self.assertEqual(p.consume((67,0),30),b'a'*32)
        self.assertEqual(p.issue((100,0),100,9,13,30)['slot'],67)

    def test_invalid_identity_epoch_or_early_return_does_not_mutate(self):
        p=C.SpillPending();p.issue((4,3),123,55,66,10)
        for sector,producer,transport,edge in [(124,55,66,35),(123,56,66,35),(123,55,67,35),(123,55,66,34)]:
            with self.assertRaisesRegex(ValueError,'identity'):p.returned((4,3),sector,producer,transport,edge,b'x'*32)
            self.assertFalse(p.raw);self.assertEqual(len(p.records),1)
        with self.assertRaises(ValueError):p.returned((4,3),123,55,66,35,None)
        p.returned((4,3),123,55,66,35,b'x'*32)
        with self.assertRaisesRegex(ValueError,'duplicate'):p.returned((4,3),123,55,66,36,b'x'*32)

    def test_one_capture_and_consume_per_PCedge_and_retained_raw_latency(self):
        p=C.SpillPending()
        for i in range(2):p.issue((i,0),i,4,5,0)
        p.returned((0,0),0,4,5,25,b'a'*32)
        with self.assertRaisesRegex(ValueError,'one response'):p.returned((1,0),1,4,5,25,b'b'*32)
        p.returned((1,0),1,4,5,26,b'b'*32)
        with self.assertRaisesRegex(ValueError,'raw capture'):p.consume((0,0),29)
        self.assertEqual(p.consume((0,0),31),b'a'*32)
        with self.assertRaisesRegex(ValueError,'one held'):p.consume((1,0),31)
        self.assertEqual(p.consume((1,0),32),b'b'*32)

    def test_bounds_and_duplicate_refused_before_allocation(self):
        p=C.SpillPending()
        for key,sector in [((4096,0),0),((0,32),0),((0,0),703125000)]:
            with self.assertRaises(ValueError):p.issue(key,sector,0,0,0)
        p.issue((0,0),0,0,0,0)
        with self.assertRaisesRegex(ValueError,'duplicate'):p.issue((0,0),1,0,0,0)

    def test_complete_cell_partition_and_protection_not_zero_filled(self):
        old=json.loads((C.ROOT/'results/uarch/qwen_rom_kv_credit_allocator_20261002/model-r4.json').read_text())
        s=C.sizing(old)
        self.assertEqual(s['FF_increment']['pending_four_FF_spill'],128*4*472)
        self.assertEqual(s['FF_increment']['assembly_extra_words'],280*787)
        for name,n in s['FF_increment'].items():self.assertEqual(n%s['replicas'][name],0)
        self.assertGreater(s['transaction_protection_um2'],0)
        self.assertGreater(s['clock_reset_collector_increment'],0)
        self.assertIsNone(s['mutable_storage_protection_area_mm2'])
        self.assertFalse(s['existing_macro_arrays_recharged'])
        self.assertAlmostEqual(s['total_known_service_mm2']-old['cells']['total_known_service_mm2'],s['delta_known_mm2'])

    def test_one_layer_finite17_cohorts68_pending85_word_bound(self):
        r=C.credit17_calendar(0,0,C.F(451*2500,3),C.A.S.PCService())
        self.assertEqual(r['cohorts'],2084);self.assertEqual(r['command_count_per_stack'],[32736]*4)
        self.assertEqual(r['owned_data_and_grant_count_per_stack'],[65472]*4)
        for field,bound in [('peak_live_cohorts',136),('peak_pending_entries_per_PC',68),('peak_words_per_group_lane_pool',85),('peak_write_slots_per_PC',4)]:
            self.assertLessEqual(r[field],bound)
        self.assertEqual(r['global_assembly_slots'],4760)
        self.assertTrue(r['all_reverse_grants_reserved'])
        self.assertFalse(r['physical_or_payload_qualification'])

if __name__=='__main__':unittest.main()
