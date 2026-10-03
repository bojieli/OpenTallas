import bisect
import json
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from dsrom_s73_pair1 import RaggedPool,physical_address

class SuccessorTests(unittest.TestCase):
    def test_real_sites_and_ragged_region_bijection(self):
        p=RaggedPool()
        self.assertEqual(list(p.fill),list(range(2682)))
        self.assertEqual(sum(len(p.byreg[(r,'q')]) for r in range(128)),2682)
        self.assertEqual(sum(len(p.byreg[(r,'bf16')]) for r in range(128)),576)
        self.assertEqual(set(len(p.byreg[(r,'q')]) for r in range(128)),{20,21})
        for r in range(128):
            for site in p.byreg[(r,'q')]:self.assertEqual(bisect.bisect_right(p.bounds,site)-1,r)

    def test_no_ROM_ECC_or_sidecar_debit(self):
        p=RaggedPool();p.reserve_ecc(1000000000000)
        self.assertEqual((p.ecc_bits,p.ecc_pairs,p.raw),(0,[],set()))
        x=p.raw_bankset(['native_HE'],20000)
        self.assertEqual(x['secded_inline_bits'],0)
        self.assertEqual(len(x['pairs']),12)
        self.assertTrue(set(x['pairs']).isdisjoint(p.bf))
        self.assertEqual(len({bisect.bisect_right(p.bounds,s)-1 for s in x['pairs']}),12)

    def test_transaction_clone_preserves_original_capacity(self):
        p=RaggedPool();t=p.clone();t.fill[0]=8192;t.raw.add(0)
        self.assertEqual(p.fill[0],0);self.assertNotIn(0,p.raw)

    def test_noecc_FP4_payload_lookup_and_bounds(self):
        m=dict(format='fp4',rows=2,K=512,segments=[(0,512)],plans=[[0,0,0,1,128,0,8]],
               rank_slices=[dict(rows=[0,2],cols=[0,512])]*4,physical_owner_ranks=[0],stage=0,
               tensor='source.weight',conversion='native')
        a=physical_address(m,3,1,511)
        self.assertEqual(a['physical_owner_rank'],0)
        self.assertTrue(a['owner_result_multicast_required'])
        self.assertEqual(a['bit_range'],[260,264])
        self.assertFalse(a['ROM_ECC'])
        with self.assertRaises(ValueError):physical_address(m,0,0,512)

    def test_artifact_conservation_and_no_admission(self):
        b=ROOT/'results/uarch/dsrom_s73_pair1_20261003/baseline_s82_successor_r1'
        if not (b/'model.json').exists():self.skipTest('Run record composition first')
        model=json.loads((b/'model.json').read_text());ledger=json.loads((b/'area_ledger.json').read_text())
        self.assertFalse(model['adopted']);self.assertFalse(model['RTL_PnR_inference'])
        self.assertEqual(ledger['complement_credit_mm2'],0)
        self.assertAlmostEqual(sum(x['mm2'] for x in ledger['terms']),ledger['historical_delta_mm2'])
        self.assertEqual(sum(x['mode']=='removed' for x in ledger['terms']),1)
        c=json.loads((b/'weight_conservation.json').read_text())
        self.assertEqual(c['shipped_source_keys'],96085)
        self.assertTrue(c['symbolic_all_shipped_provider_coverage_PASS'])
        self.assertEqual(c['unplaced_keys'],[])
        self.assertFalse(c['physically_placed_exactonce_PASS'])
        self.assertTrue(c['matrix_code_coordinates_exactonce_PASS'])
        multicast=json.loads((b/'indexer_multicast_model.json').read_text())
        self.assertEqual(len(multicast['calls']),20)
        self.assertGreater(multicast['additional_token_us_lower'],0)
        self.assertEqual(multicast['frame_credit_mm2'],0)
        baseline=json.loads((b/'return_baseline.json').read_text())
        self.assertEqual((baseline['RD'],baseline['ROOTD'],baseline['existing_storage_NP']),(64,128,4096))
        self.assertEqual(baseline['rejected_RD4_reuse_cycles'],9)
        self.assertFalse(baseline['RD4_credit_area_or_gain_claim'])
        self.assertGreater(baseline['FF50_reservation_mm2'],52)
        self.assertEqual(baseline['weight_padding_pairs'],0)
        self.assertGreater(ledger['sensitivity']['source_classified']['S73']['screen_mm2'],858)
        self.assertTrue(model['candidate_inventory']['additional_stage_hops_only_not_complete_token_delta'])
        aux=json.loads((b/'auxiliary_map.json').read_text())
        for t in aux['tensors']:
            end=0
            for s in t['payload_spans']:
                self.assertEqual(s['source_byte_range'][0],end)
                end=s['source_byte_range'][1]
                self.assertLessEqual(s['pair_data_byte_range'][1],524288)
            self.assertEqual(end,t['source_storage_bytes'])

if __name__=='__main__':unittest.main()
