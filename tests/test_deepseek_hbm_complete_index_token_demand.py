from pathlib import Path
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import deepseek_hbm_complete_index_token_demand as T
class TokenDemand(unittest.TestCase):
    def test_actual_sourceprogram_index_counts_not_fixture_multiplier(self):
        calls=T.inventory()
        self.assertEqual([c['layer'] for c in calls],[2,8,14,20,24,28,32,36])
        self.assertEqual([c['program_pc'] for c in calls],[125,453,786,1114,1337,1558,1779,2000])
        self.assertEqual([c['KV_source_layer'] for c in calls],[2,8,14,20,20,20,20,20])
        self.assertEqual(sum(sum(r['owned_keys'] for r in c['ranks']) for c in calls),6815744)
        self.assertEqual(sum(sum(r['total_tiles'] for r in c['ranks']) for c in calls),106848)
        self.assertEqual(sum(sum(r['full64_tiles'] for r in c['ranks']) for c in calls),106080)
        for r in range(96):self.assertEqual(sum(c['ranks'][r]['total_tiles'] for c in calls),1113)
        self.assertEqual(sorted({r['tail_keys'] for c in calls for r in c['ranks']}),[16,24,40,48])
    def test_fixed_resource_geometry_and_unqualified_clock(self):
        r=T.resources()
        self.assertEqual((r['SMs_per_rank_die'],r['FP32_SIMT_lanes_per_SM'],r['partitions_per_SM']),(32,128,4))
        self.assertEqual(r['shared_combined_bytes_per_SM_serial_cycle'],128)
        self.assertEqual((r['RF_read_bits_per_SM_serial_cycle'],r['RF_logical_write_bits_per_SM_serial_cycle']),(8192,4096))
        self.assertEqual(r['implemented_general_SIMD_lanes'],0)
        self.assertFalse(r['physical_clock_qualified'])
    def test_owned_granules_and_partial_global_tail(self):
        for count in [0,1,7,8,9,767,768,769,524288,1048576]:
            self.assertEqual(sum(T.owned_count(count,r) for r in range(96)),count)
        self.assertEqual(T.owned_count(524288,0),5464)
        self.assertEqual(T.owned_count(524288,95),5456)
    def test_mandatory_bridge_padding_ABI_not_zero(self):
        c=T.local2_cost();a=c['mandatory_added_shared_events']
        self.assertEqual(c['cold_shared_bytes_per_SM_two_keys'],295756)
        self.assertEqual(c['cold_shared_warp_issues_per_SM_two_keys'],2574)
        self.assertEqual(a['finite_result_register_to_shared']['bytes'],1024)
        self.assertEqual(a['F32_to_F64_ABI']['bytes'],384)
        self.assertIsNone(c['provider_sector32_half_sector_merge_or_RMW_cost'])
        self.assertFalse(c['whole_dispatcher_demand_complete'])
    def test_cache_model_fits_only_under_declared_proposal(self):
        c=T.cache_layout();self.assertEqual(c['arena_bytes_per_SM'],55296)
        self.assertTrue(c['capacity_only_fit'])
        self.assertFalse(c['full_query_cache_software_exact_gate'])
        self.assertFalse(c['model_adoption'])
        self.assertEqual(c['regions_per_SM']['q_exp']['bytes'],512)
        self.assertEqual(c['regions_per_SM']['output']['bytes'],256)
    def test_perrank_effect_and_provider_no_hardware_claim(self):
        m=T.build();r=m['rank_token_demand'][0]
        self.assertEqual(r['owned_key_scores'],71032)
        self.assertEqual(r['cold_SM0_requested_shared_bytes'],329176428)
        self.assertEqual(r['proposed_querycache_SM0_requested_shared_bytes'],202158888)
        self.assertIsNone(m['actual_physical_service_cycles'])
        self.assertIsNone(m['whole_token_baseline_or_rate_credit'])
        self.assertFalse(m['dispatcher_binding_authorized'])
