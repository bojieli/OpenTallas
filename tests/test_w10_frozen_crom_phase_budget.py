import copy
from pathlib import Path
import unittest
from tools.w10_frozen_crom_phase_budget import build
from tools.w10_crom_control_reservation import read
class FrozenPhaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        specs={'frozen':('64a04715c','results/quality/w16_engram_initializer_20261001/frozen_closure.json'),'local':('47b715428','results/quality/w16_w17_crom_finite_prefetch_20261001/local_home.json'),'base':('cda48d1f7','results/uarch/w10_crom_staging_correction_r1/budget.json'),'controls':('ebef36895','results/uarch/w10_crom_control_reservation_r1/budget.json'),'calendar':('bc1ec8b8f','results/quality/w16_w17_crom_finite_prefetch_20261001/calendar.json'),'power':('e79394b1c','results/uarch/w10_q_power_envelope_r1/power.json'),'clock':('fea811df4','results/uarch/w10_q_existing_icg_r1/clock.json'),'area':('6da3c7a60','results/uarch/w10_q_elaboration_inventory_r1/construction.json')}
        cls.r={k:read(c,p)[0] for k,(c,p) in specs.items()};cls.x=build(**cls.r)
    def test_selected_output_not_135_broadcast(self):
        self.assertEqual(self.x['phase_service_floors_fast_cycles'],{'all_words':34360,'gamma_all':25920,'single_gamma_home':320})
        r=copy.deepcopy(self.r);r['frozen']['finite_service']['selected_FP32_outputs_per_fast_cycle']=135
        with self.assertRaises(ValueError):build(**r)
    def test_fresh_local_inventory_both_controls_and_catalog(self):
        self.assertEqual([r['total_FF_bits'] for r in self.x['rows']],[500588,503282,670196])
        for r in self.x['rows']:
            s=r['storage_FF_by_role'];self.assertEqual(s['payload_route'],11264)
            self.assertEqual(s['forward_control_route'],704)
            self.assertEqual(s['reverse_control_route_and_ACK_serialization'],768)
            self.assertEqual(r['macro_count_including_catalog'],61)
            self.assertEqual(r['total_FF_bits'],sum(s.values()))
    def test_imagehole_and_fit_not_labels_or_margin(self):
        self.assertEqual(self.x['source_invalid_hole'],[508800,529280])
        self.assertFalse(self.x['physical_admission']);self.assertFalse(self.x['complete_phase_budget'])
        self.assertEqual(self.x['local_fit']['placement_verdict'],'REJECT_UNRESERVED_SU_DISPLACEMENT')
        self.assertIsNone(self.x['phase_composition']['whole_point_power_margin_W'])
        self.assertEqual(self.x['phase_composition']['adaptive_clock_gate_credit'],0)
        self.assertEqual(self.x['phase_composition']['historical_power_subtraction_W'],0)
    def test_floor_energy_does_not_claim_fulltoken(self):
        self.assertIsNone(self.x['whole_token_latency_cycles'])
        self.assertTrue(self.x['phase_composition']['mandatory_macro_CLK_energy_retained'])
        self.assertIsNone(self.x['phase_composition']['actual_resident_home_count_and_intervals'])
