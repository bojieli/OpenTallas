import fnmatch
import gzip
import json
from pathlib import Path
import re
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import model_dsrom_selector_allowed_terminal as P


class AllowedTerminal(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.model=P.build();cls.old=json.loads(P.OLD.read_text())

    def test_byte_exact_replay(self):
        self.assertEqual(json.dumps(self.model,indent=2,sort_keys=True)+'\n',(P.BASE/'model.json').read_text())

    def test_actual_policy_excludes_old_allows_replacement(self):
        patterns=P.policy();r=self.model['replacement']
        self.assertTrue(any(fnmatch.fnmatchcase(r['old_master'],p) for p in patterns))
        self.assertFalse(any(fnmatch.fnmatchcase(r['new_master'],p) for p in patterns))
        self.assertFalse(self.model['policy']['changed'])

    def test_actual_SS_FF_functions_preserve_noninverting_logic(self):
        for corner in ('SS','FF'):
            text=gzip.decompress((P.C.BASE/'inputs'/f'asap7sc7p5t_INVBUF_RVT_{corner}_nldm_220122.lib.gz').read_bytes()).decode()
            functions=[]
            for master in ('HB2xp67_ASAP7_75t_R','BUFx4_ASAP7_75t_R'):
                pin=P.C.group(P.C.group(text,'cell',master),'pin','Y')
                functions.append(re.search(r'function\s*:\s*"([^"]+)"',pin)[1])
            self.assertEqual(functions,['A','A'])

    def test_fixed_state_edges_ports_and_reach(self):
        f=self.model['fixed'];p=self.old['placement_contract']
        self.assertEqual((f['data_FF'],f['valid_ASR'],f['INV']),(475954,226,476180))
        self.assertEqual((f['data_repeater_BUF'],f['terminal_BUF'],f['terminal_HB']),(965012,476180,0))
        self.assertEqual((f['input_edges'],f['return_edges'],f['write_edges']),(99,99,28))
        self.assertEqual(f['transport_cycles_per_call'],226)
        self.assertEqual(f['ninecall_increment'],3312)
        self.assertEqual(f['maximum_remote_span_um'],p['maximum_remote_span_um'])
        self.assertEqual(f['remaining_half_pool_tracks'],[28,38])
        self.assertEqual(self.model['cost']['additional_state_bits'],0)
        self.assertEqual(self.model['cost']['additional_cycles'],0)

    def test_unchanged_uncertainty_and_fixed_screens(self):
        ss=self.model['SS_conditional_screen'];ff=self.model['FF_conditional_screen']
        self.assertEqual((ss['period_ps'],ss['setup_uncertainty_ps'],ss['additional_skew_budget_ps']),(833,60,25))
        self.assertEqual((ff['hold_uncertainty_ps'],ff['additional_capture_skew_budget_ps']),(25,25))
        self.assertAlmostEqual(ss['stage_upper_ps'],717.6180229121435)
        self.assertLess(ss['destination_slew_ps'],320)
        for label,margin in [('data_FF',9.05266),('valid_FF',10.45516)]:self.assertAlmostEqual(ff['zero_wire_hold_margins_ps'][label],margin)
        self.assertTrue(ff['physical_min_load_and_slew_not_proven'])
        self.assertFalse(ff['subgrid_extrapolation_credit'])

    def test_area_and_site_delta_charged_once(self):
        cost=self.model['cost']
        self.assertAlmostEqual(cost['cell_area_delta_um2'],476180*(.10206-.0729))
        self.assertAlmostEqual(cost['reserve_delta_mm2_at50pct'],.0277708176)
        self.assertAlmostEqual(cost['station_reservation_mm2_at50pct'],.62337924324)
        self.assertEqual(cost['terminal_site_width_delta_DBU'],108)
        self.assertEqual(cost['terminal_site_width_delta_DBU']//54,2)
        self.assertTrue(cost['old_station_replaced_not_added'])

    def test_no_placement_or_HDL_qualification(self):
        for key in ('RTL_build_admitted','PR_admitted','HDL_equivalence','extracted_SS_FF'):self.assertFalse(self.model[key])
        self.assertTrue(self.model['construction']['legal_sites_not_allocated'])
        self.assertTrue(self.model['construction']['caller_guard19_cells_remain_separately_charged'])
        self.assertEqual(P.sha(P.OLD.read_bytes()),P.OLD_SHA)


if __name__=='__main__':unittest.main()
