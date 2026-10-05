import json
import ast
from pathlib import Path
import subprocess
import sys
import tempfile
import shutil
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import model_dsrom_selector_join_admissibility as T


class Joined(unittest.TestCase):
    def test_existing_incremental_state_disjoint(self):
        s=T.build()['state']
        self.assertEqual(s['existing_core_model_bits']+s['incremental_core_bits'],s['proposed_core_gross_bits'])
        self.assertEqual(s['proposed_cut_gross_bits'],475954+226)
        self.assertEqual(s['total_proposed_core_plus_cut_bits'],1174534)
        self.assertEqual(s['total_incremental_core_plus_cut_bits'],603320)
        self.assertNotEqual(s['incremental_core_bits'],s['proposed_cut_gross_bits'])

    def test_independent_clock_floor_no_core_omission(self):
        m=T.build();c=m['clock']
        self.assertEqual(c['station_fanout_floor']['BUF_cells'],48007)
        self.assertEqual(c['additional_core_fanout_floor']['BUF_cells'],70406)
        self.assertEqual(c['clock_buffer_floor_sum'],118413)
        self.assertEqual(c['combined_model_sinks'],1174534)
        self.assertEqual(c['conditional_independent_floor_roots'],2)
        self.assertIsNone(c['actual_parent_root_count'])
        self.assertIsNone(c['named_tree_sites_and_spatial_distribution'])

    def test_cell_reservation_replaces_once_and_not_occupied_area(self):
        a=T.build()['area']
        parts=['complete_replacement_core','allowed_station_including_station_clock_floor',
               'explicit_control_guards','core35_ASR_plus_ties_debit','cut229_ties']
        self.assertAlmostEqual(sum(a[k] for k in parts),2.30583140316)
        self.assertAlmostEqual(a['proposed_finite_cell_reservation_with_core_clock_floor'],2.32020267588)
        self.assertIsNone(a['actual_combined_occupied_area'])
        self.assertIsNone(a['full_clock_reset_PG_pin_access_wire_hold_repair_reservation'])

    def test_finite_slot_does_not_silently_hide_clock(self):
        s=T.build()['slot']
        self.assertAlmostEqual(s['current_selector_slot_mm2'],1.6848787968)
        self.assertAlmostEqual(s['deficit_if_all_core_clock_floor_colocated_mm2'],0.01192127868)
        self.assertIsNone(s['core_clock_floor_home'])
        self.assertIsNone(s['whole_reticle_area_delta'])

    def test_tracks_guards_and_present_counts_not_physical_credit(self):
        m=T.build();t=m['tracks'];f=m['fanout']
        self.assertEqual(t['proposed_main_corridor_total'],4214)
        self.assertEqual((t['horizontal_remaining'],t['vertical_remaining']),(28,38))
        self.assertEqual(t['formed_write_bits_plus_present'],2114)
        self.assertIsNone(t['actual_remaining_tracks_after_all_physical_obstructions'])
        self.assertFalse(t['physical_fit'])
        self.assertEqual((f['SETN_providers_cut'],f['source_present_ties'],f['core_incremental_SETN_providers']),(226,3,35))
        self.assertEqual(f['cut_reset_guard_AND_sinks'],7)
        self.assertIsNone(f['baseline_core_RESETN_sinks'])

    def test_source_exact_instance_and_fence_deadline_null(self):
        m=T.build()
        self.assertIn('g_write_station.u_write',m['station_binding']['actual_source_instances'])
        self.assertNotIn('g_write_station.u_write28',m['station_binding']['actual_source_instances'])
        self.assertEqual(m['deadline']['nine_call_increment'],3312)
        for k in ('actual_consumer_deadline','actual_last_VM_write_edge','root_home_visibility_edge','implemented_CDC'):
            self.assertIsNone(m['deadline'][k])
        self.assertFalse(m['deadline']['new_ACK'])
        self.assertTrue(m['deadline']['default1024_timeout_FAIL_preserved'])
        self.assertTrue(m['deadline']['capture_e899_FAIL_preserved'])
        self.assertFalse(any(m['admissions'].values()))

    def test_source_backend_exception_and_scope_exact(self):
        b=T.build()['backend']
        self.assertEqual(b['official_UDP_binary_transition_cases'],72)
        self.assertTrue(b['UDP_tables_supported'])
        self.assertTrue(b['delayed_setuphold_outputs_lowered_to_assignments'])
        self.assertFalse(b['physical_timing_checks_enforced'])
        self.assertFalse(b['mappedprimitive_runtime_PASS'])
        self.assertFalse(b['simultaneous_input_delta_events_qualified'])
        self.assertFalse(b['behavioral_cell_replacement'])

    def test_delayed_output_or_UDP_backend_mutant_refused(self):
        seq=(T.ROOT/T.PATHS['seq']).read_text()
        width=(T.BASE/'inputs/V3Width.cpp').read_text()
        udp=(T.BASE/'inputs/V3Udp.cpp').read_text()
        language=(T.BASE/'inputs/languages.rst').read_text()
        for w,u in [(width.replace('nodep->refevp(), nodep->delrefp()','removed'),udp),
                    (width,udp.replace('visit(AstUdpTable*','removed'))]:
            with self.assertRaises(ValueError):T.primitive_review(seq,w,u,language)

    def test_official_binary_capture_and_reset_mutants_refused(self):
        seq=(T.ROOT/T.PATHS['seq']).read_text()
        width=(T.BASE/'inputs/V3Width.cpp').read_text()
        udp=(T.BASE/'inputs/V3Udp.cpp').read_text()
        language=(T.BASE/'inputs/languages.rst').read_text()
        for a,b in [('? (01) 1 ? : ? : 1;','? (01) 1 ? : ? : 0;'),
                    ('?  ?   ?   1   0   ? : ? : 1;','?  ?   ?   1   0   ? : ? : 0;')]:
            self.assertIn(a,seq)
            with self.assertRaises(ValueError):T.primitive_review(seq.replace(a,b),width,udp,language)

    def test_cold_fresh_replay_no_git_or_owner_path(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); pending=['model_dsrom_selector_join_admissibility'];seen=set()
            def copy(relative):
                dst=root/relative;dst.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(T.ROOT/relative,dst)
            while pending:
                name=pending.pop();relative='tools/'+name+'.py';source=T.ROOT/relative
                if name in seen or not source.exists():continue
                seen.add(name);copy(relative)
                for node in ast.walk(ast.parse(source.read_text())):
                    if isinstance(node,ast.Import):pending.extend(x.name for x in node.names)
                    if isinstance(node,ast.ImportFrom) and node.module:pending.append(node.module)
            for relative in T.PATHS.values():copy(relative)
            for source in T.BASE.rglob('*'):
                if source.is_file():copy(str(source.relative_to(T.ROOT)))
            p=root/'fresh.json'
            result=subprocess.run([sys.executable,str(root/'tools/model_dsrom_selector_join_admissibility.py'),'--out',str(p)],cwd=d,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(json.loads(p.read_text()),T.build())
            self.assertEqual(p.read_bytes(),(T.BASE/'model_r2.json').read_bytes())


if __name__=='__main__':unittest.main()
