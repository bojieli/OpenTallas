import copy
import gzip
import json
from pathlib import Path
import unittest
from write_itinerary import compile_itinerary, verify_itinerary

ROOT=Path(__file__).resolve().parents[2]


class WriteItineraryTests(unittest.TestCase):
    def setUp(self):
        self.requests=dict(events=[dict(id=str(i),kind='write',client='su',slot=i,job=0,tag=1,
                                       row=32*i,mask=1<<i,issue_cycle=10) for i in range(3)])
        self.contract=dict(bank_mapping='rowmod',capture_to_drain_min_cycles=1,drain_to_macro_commit_cycles=5)

    def test_fixed_three_write_collision_compiles_without_runtime_arbitration(self):
        before=copy.deepcopy(self.requests)
        result=compile_itinerary(self.requests,self.contract)
        self.assertEqual([r['scatter_issue_cycle'] for r in result['rows']],[11,12,13])
        self.assertEqual([r['macro_commit_cycle'] for r in result['rows']],[16,17,18])
        self.assertEqual(result['bank_storage_slots'],{'0':3})
        self.assertEqual(result['maximum_extra_bank_serialization_cycles'],2)
        self.assertEqual(verify_itinerary(self.requests,result)['status'],'pass')
        self.assertEqual(before,self.requests)
        self.assertFalse(result['dispatch_eligible'])

    def test_mask_or_storage_mutants_fail_independent_table_check(self):
        result=compile_itinerary(self.requests,self.contract)
        result['rows'][0]['mask']=65535
        self.assertIn('source_port_or_payload_identity',verify_itinerary(self.requests,result)['violations'])
        result=compile_itinerary(self.requests,self.contract)
        result['rows'][1]['capture_storage_slot']=0;result['rows'][1]['drain_storage_slot']=0
        self.assertIn('live_storage_overwrite',verify_itinerary(self.requests,result)['violations'])

    def test_service_collision_and_dropped_write_mutants_fail(self):
        result=compile_itinerary(self.requests,self.contract)
        result['rows'][1]['scatter_issue_cycle']=11
        self.assertIn('bank_write_service_collision',verify_itinerary(self.requests,result)['violations'])
        result=compile_itinerary(self.requests,self.contract);result['rows'].pop()
        self.assertIn('write_identity_coverage',verify_itinerary(self.requests,result)['violations'])

    def test_same_edge_overlapping_words_reject_implicit_priority(self):
        self.requests['events'][1].update(row=0,mask=1)
        result=compile_itinerary(self.requests,self.contract)
        self.assertIn('same_edge_word_alias',[v['kind'] for v in result['violations']])

    def test_missing_native_deadlines_remain_explicit(self):
        result=compile_itinerary(self.requests,self.contract)
        self.assertEqual(result['missing_native_visibility_deadlines'],3)
        self.requests['events'][0]['deadline_cycle']=15
        result=compile_itinerary(self.requests,self.contract)
        self.assertIn('missed_native_write_visibility',[v['kind'] for v in result['violations']])

    def test_all_four_actual_itinerary_tables_are_internally_legal(self):
        base=ROOT/'results/arch/s81_native_compile_1014/write_itineraries'
        for layer,expected in [('L0',2091),('L2',2603),('L14',2603),('L20',2603)]:
            result=json.loads(gzip.decompress((base/f'{layer}.json.gz').read_bytes()))
            requests=dict(events=[dict(id=r['id'],kind='write',client=r['source_port']['client'],
                                       slot=r['source_port']['slot'],job=r['job'],tag=r['tag'],row=r['row'],
                                       mask=r['mask'],issue_cycle=r['capture_cycle']) for r in result['rows']])
            self.assertEqual(len(result['rows']),expected)
            self.assertEqual(result['total_reserved_storage_slots'],68)
            self.assertEqual(result['peak_live_storage_rows'],18)
            self.assertEqual(result['maximum_extra_bank_serialization_cycles'],2)
            self.assertEqual(verify_itinerary(requests,result)['status'],'pass')
            self.assertFalse(result['dispatch_eligible'])


if __name__=='__main__':
    unittest.main()
