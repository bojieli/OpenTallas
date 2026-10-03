import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import prepare_dsrom_full_selector_allowed_cut_gate as P


class FullCuts(unittest.TestCase):
    def test_one_selected_c9_clock_bank_no_annex_recharge(self):
        m=P.context();c=m['selected_clock_bank']
        self.assertEqual(m['site_instances'],70406)
        self.assertEqual(c['core_clock70406'],70406)
        self.assertEqual(c['named_bank_bbox_DBU'],[3129786,8953200,3147930,9745920])
        self.assertAlmostEqual(c['reserved_bank_mm2'],0.01438311168)
        self.assertEqual(m['raw_clock_corrections_separate_not_selector_recharge'],68614)
        self.assertFalse(m['literal_source_to_clock_site_assignment_present'])
        self.assertFalse(m['c9_physical_admitted']);self.assertIsNone(m['c9_consumer_deadline'])

    def test_full_state_and_area_already_priced_no_new_engine(self):
        m=json.loads((P.BASE/'component_model.json').read_text())
        self.assertEqual(m['core_model_bits']+m['transport_payload_FF']+m['transport_ASR_present_FF'],1174534)
        self.assertEqual(m['engine_state_or_stage_or_port_increment'],0)
        self.assertEqual(m['geometry'],dict(N=4,NMAX=2048,LDW=4,P=64,PF=64,DIG=8,CB=14))
        self.assertEqual(m['cut_edges'],[99,99,28])
        self.assertEqual(m['total_per_call_increment'],368)
        self.assertFalse(m['physical_admitted']);self.assertFalse(m['timeout4096_adopted'])

    def test_exact_three_bench_replacements_no_assertion_loosen(self):
        old=(P.G.BASE/'gate_r4/fixture/bench_dsrom_balanced_selector_gate_prepare.sv').read_text()
        new=P.mapped_bench(old)
        inverse=new.replace('module bench_dsrom_full_selector_allowed_cut_prepare #(',
                            'module bench_dsrom_balanced_selector_gate_prepare #(')
        inverse=inverse.replace('ot_w15_coll_dma_balanced_allowed_cut_prepare #(',
                                'ot_w15_coll_dma_balanced_station_prepare #(')
        inverse=inverse.replace('.TK_CELL_MAP(MUTANT==4?0:1),','')
        self.assertEqual(inverse,old)
        self.assertEqual(new.count('.TK_CELL_MAP(MUTANT==4?0:1)'),1)
        self.assertEqual(new.count('fault_case('),old.count('fault_case('))
        self.assertEqual(new.count('$fatal'),old.count('$fatal'))
        with self.assertRaises(ValueError):P.mapped_bench(old.replace('.TK_BALANCED(MUTANT==4?0:1)','removed'))

    def test_pinned_old_gate_and_cut_packages_reproduced_exactly(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'package';P.prepare(out)
            for generated,old in [('gate',P.G.BASE/'gate_r4'),('allowed',P.C.BASE/'package_r2')]:
                manifest=json.loads((old/'artifact_manifest.json').read_text())
                for relative,h in manifest.items():
                    self.assertEqual(P.V.sha((out/generated/relative).read_bytes()),h,relative)
            self.assertEqual((out/'gate/fixture/inputs/case_00.mem').read_bytes(),
                             (P.G.BASE/'gate_r4/fixture/inputs/case_00.mem').read_bytes())

    def test_selected_inventory_has_only_one_candidate_and_official_libraries(self):
        plan=json.loads((P.BASE/'package/sourceplan.json').read_text());inventory=plan['source_inventory']
        self.assertEqual(len(inventory),12);self.assertEqual(len(set(inventory)),12)
        self.assertNotIn('gate/fixture/bench_dsrom_balanced_selector_gate_prepare.sv',inventory)
        self.assertNotIn('gate/candidate/ot_w15_coll_dma_balanced_station_prepare.sv',inventory)
        self.assertIn('allowed/candidate/ot_w15_coll_dma_balanced_allowed_cut_prepare.sv',inventory)
        self.assertIn('allowed/candidate/ot_topk_allowed_cut_packet_prepare.sv',inventory)
        self.assertEqual(len([p for p in inventory if '/library_sources/' in p]),3)
        self.assertFalse(plan['core_physical_cell_mapping_qualified'])

    def test_same_full_fault_expected_and_defaultoff_contract(self):
        plan=json.loads((P.BASE/'package/sourceplan.json').read_text())
        self.assertEqual(plan['prepared_counts'],dict(legal_cases=37,reset_aborts=4,fault_cases=15,mutants=3,defaultoff_cases=37))
        self.assertEqual(plan['profiles'],[0,1,2,3,4])
        self.assertTrue(plan['same_complete_fault_contract'])
        self.assertTrue(plan['same_independent_expected_values'])
        self.assertTrue(plan['primitive_gate_PASS_required'])
        self.assertFalse(plan['integrated_parent_admitted'])
        self.assertFalse(plan['compile_GO'])

    def test_every_generated_artifact_hash_and_fresh_replay(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'package';P.prepare(out)
            self.assertEqual((out/'artifact_manifest.json').read_bytes(),(P.BASE/'package/artifact_manifest.json').read_bytes())
            for relative,h in json.loads((out/'artifact_manifest.json').read_text()).items():
                self.assertEqual(P.V.sha((out/relative).read_bytes()),h)

    def test_dependencies_in_current_main_no_primitive_import_required(self):
        base='75c71c1b3d885face9b93c2637e8d747d7c7ec6e'
        for module in [P.G,P.C,P.V,P.G.C,P.G.C.F]:
            path=Path(module.__file__).relative_to(P.ROOT)
            raw=subprocess.check_output(['git','show',base+':'+str(path)],cwd=P.ROOT)
            self.assertEqual(raw,(P.ROOT/path).read_bytes())


if __name__=='__main__':unittest.main()
