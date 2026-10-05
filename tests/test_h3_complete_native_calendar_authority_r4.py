import copy
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('authority_r4_tests',ROOT/'tools/h3_complete_native_calendar_authority_r4.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class AuthorityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base=ROOT/m.OUT;cls.manifest,cls.data=m.read_inputs(cls.base)
        cls.result=m.reconcile(cls.base)
    def test_three_distinct_authorities_exact_replay(self):
        rows=self.result['authorities'];self.assertEqual(len(rows),3)
        self.assertEqual(rows[0]['clock_hz'],1033900000)
        self.assertEqual(rows[1]['result']['total_us'],495.23)
        self.assertEqual(rows[2]['result']['total_us'],442.14)
        self.assertEqual(rows[2]['unfused_result']['total_us'],458.46)
        self.assertEqual(rows[2]['result']['parts_us']['fetch'],5.33)
        self.assertEqual(self.result['exact_program']['operations'],2213)
        self.assertFalse(self.result['hardware_qualified'])
    def test_all8_frozen_records_and_missing_current_paths_preserved(self):
        self.assertEqual(len(self.result['all8_frozen_record_pins']),8)
        selected=self.result['authorities'][2]
        self.assertTrue(selected['current_fused_record_missing'])
        self.assertTrue(selected['current_unfused_record_missing'])
        self.assertFalse(self.result['authoritative_headline_selected'])
    def test_wrong_source_or_input_pin_rejected(self):
        record=json.loads(self.data['selected_fused']);m.verify_record_inputs(record,self.manifest)
        bad=copy.deepcopy(record);bad['inputs']['results/rtl/w15_hbm_nvls.json']='0'*64
        with self.assertRaisesRegex(ValueError,'unresolved'):m.verify_record_inputs(bad,self.manifest)
    def test_retained_byte_mutation_rejected(self):
        with tempfile.TemporaryDirectory()as name:
            base=Path(name);shutil.copytree(self.base/'inputs',base/'inputs');shutil.copy(self.base/'input_manifest.json',base/'input_manifest.json')
            path=base/'inputs'/self.manifest['selected_select']['archive'];path.write_bytes(path.read_bytes()+b' ')
            with self.assertRaisesRegex(ValueError,'hash'):m.read_inputs(base)
    def test_fetch_paid_once_and_replacement_scope(self):
        program=json.loads(__import__('gzip').decompress(self.data['results/rtl/w19_hbm_tp96_program_oreduce.json'])) if self.data['results/rtl/w19_hbm_tp96_program_oreduce.json'][:2]==b'\x1f\x8b' else json.loads(self.data['results/rtl/w19_hbm_tp96_program_oreduce.json'])
        paid=m.charge_fetch_once(program,fetch_paid=True,ns_per_fetch=133.2)
        self.assertEqual(paid['source_fetch_ops'],40);self.assertEqual(paid['incremental_us'],0)
        unpaid=m.charge_fetch_once(program,fetch_paid=False,ns_per_fetch=133.2)
        self.assertAlmostEqual(unpaid['incremental_us'],5.328)
        for cost in (0,-1,None,float('nan')):
            with self.assertRaises(ValueError):m.charge_fetch_once(program,fetch_paid=True,ns_per_fetch=cost)
    def test_collective_geometry_and_delta_cannot_qualify_wide_slots(self):
        self.assertEqual(self.result['collective_geometry']['product_slot_bytes'],749.7)
        self.assertFalse(self.result['collective_geometry']['wide_slot_is_literal_physical_word'])
        self.assertEqual(self.result['deltas_same_W19_program'],dict(historical_to_selected_collective_us=-43.27,local_recipe_change_unfused_us=6.5,selected_lane_fusion_saving_us=16.32,fetch_change_us=0.0))
        self.assertTrue(self.result['refresh']['replacing_case_requires_subtract_paid_case_before_adding_new_case'])

if __name__=='__main__':unittest.main()
