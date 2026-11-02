"""Exercise Tcl serialization and refuse incomplete or mismatched clock evidence."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
import child_clock_witness as witness


class NativeWitness(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.tools = self.root / 'tools'
        self.tools.mkdir()
        (self.tools / 'clock_family.tcl').write_text('')
        (self.tools / 'pair_skew.tcl').write_text(r'''
namespace eval sta {proc worst_slack_cmd {mode} {return 0}}
proc ot_ps_regs {} {
 set ::ot_ps_noarr 0
 set ::ot_ps_insertion [dict create clk {0 0}]
 return [dict create {ff[0]} {{ff[0]/CLK} clk 240 225 rise} ff1 {ff1/CLK clk 245 230 rise}]
}
proc ot_ps_related {R} {return [list [dict create pair [list {ff[0]} ff1 ff1/D 10 20 ff1]] 1 0 2]}
proc get_pins {name} {return $name}
proc get_cells {args} {return [lindex $args end]}
proc get_property {object field} {
 if {$field eq "ref_name"} {return DFFHQNx1_ASAP7_75t_R}
 if {$object eq "vclk"} {return {}}
 if {$field eq "sources"} {return ck}
 error "unexpected property"
}
proc all_clocks {} {return {clk vclk}}
proc get_full_name {object} {return $object}
proc get_ports {args} {return ck}
''')
        self.base = self.root / 'base'
        self.base.mkdir()
        for name in ['6_final.odb', '6_final.spef', '6_final.v', '6_final.sdc', 'cells.lib']:
            (self.base / name).write_text('fixture identity:' + name)
        self.out = self.root / 'view'
        self.out.mkdir()
        for corner in ['tt', 'ff']:
            body = witness.tcl(self.tools, corner, [str(self.base / 'cells.lib')], [str(self.base / '6_final.sdc')])
            body = body.replace('/out/', str(self.out) + '/')
            script = self.out / f'export_{corner}.tcl'
            script.write_text(body)
            run = subprocess.run(['tclsh', str(script)], capture_output=True, text=True, check=True)
            (self.out / f'export_{corner}.log').write_text(run.stdout)
            (self.out / f'leaf_{corner}.lib').write_text('exported actual model:' + corner)
        self.export = {'sdc_sequence': {c: {'tcl': ['read_sdc /native/6_final.sdc']} for c in ['tt', 'ff']}}

    def record(self):
        return witness.record(self.out, self.base, 'leaf', self.export)

    def test_tcl_roundtrip_keeps_native_bus_ids_sources_and_unqualified_scope(self):
        self.record()
        doc = json.loads((self.out / 'child_clock_witness.json').read_text())
        self.assertEqual(doc['qualification'], 'NOT_ASSERTED')
        self.assertEqual(doc['source_equivalence'], 'NOT_ASSERTED')
        self.assertEqual(doc['hierarchical_expansion'], 'NOT_ASSERTED')
        self.assertEqual(doc['corners']['tt']['counts']['pairs'], 1)
        self.assertIn('ff[0]\tff[0]/CLK\tclk\t240\t225\trise', (self.out / 'child_clock_tt_endpoints.tsv').read_text())
        self.assertIn('clk\tport\tck', (self.out / 'child_clock_tt_clocks.tsv').read_text())
        self.assertEqual(doc['native']['6_final.v'], witness.sha(self.base / '6_final.v'))

    def test_passive_reuse_cannot_make_another_timing_or_fanin_query(self):
        library=self.base/'cells.lib'
        body=witness.tcl(self.tools,'tt',[],[str(self.base/'6_final.sdc')],reuse_graph=True,library_variable='already_loaded_libs')
        setup=(self.tools/'pair_skew.tcl').read_text()+"\nset ::ot_ps_R [ot_ps_regs]\nlassign [ot_ps_related $::ot_ps_R] ::ot_ps_retained_pairs np nx nd\nset ::ot_ps_retained_counts [list $np $nx $nd]\n"
        setup+='proc ot_ps_regs {} {error "second endpoint census"}\nproc ot_ps_related {R} {error "second fanin walk"}\nproc sta::worst_slack_cmd {mode} {error "extra timing update"}\n'
        setup+=f'set already_loaded_libs {{{library}}}\n'
        script=self.out/'passive.tcl'
        script.write_text(setup+body.replace('/out/',str(self.out)+'/'))
        subprocess.run(['tclsh',str(script)],capture_output=True,text=True,check=True)

    def parent_request(self, limit=0):
        self.export['parent_boundary_request']={'instances':['ff[0]'],'std_query_limit':limit}
        for c in ['tt','ff']:
            (self.out/f'child_clock_{c}_parent_targets.tsv').write_text('instance\nff[0]\n')
            (self.out/f'child_clock_{c}_parent_relations.tsv').write_text('launch_data_pin\tcapture_data_pin\tlaunch_clock_ref\tsetup_capture_clock_ref\thold_capture_clock_ref\nff[0]/Q\tff1/D\tff[0]\tff1\tff1\n')

    def test_parent_relation_is_clock_identity_only_without_std_request(self):
        self.parent_request()
        self.record()
        doc=json.loads((self.out/'child_clock_witness.json').read_text())
        info=doc['corners']['tt']['parent_boundary_relations']
        self.assertEqual(info['relations'],1)
        self.assertEqual(info['std_slack'],'NOT_ASSERTED_BY_CLOCK_RELATIONS')
        self.assertNotIn('std_path_evidence',info)

    def test_requested_std_cannot_reuse_a_clock_only_relation(self):
        self.parent_request(10)
        with self.assertRaisesRegex(ValueError,'incomplete original-STD'):
            self.record()

    def make_exact_parent_std(self):
        self.parent_request(10)
        header='launch_data_pin capture_data_pin delay status actual_startpoint actual_endpoint check_role native_std_slack_ps launch_clock_pin launch_clock launch_pin_edge launch_source_pin launch_source_edge launch_source_insertion_ps capture_clock_pin capture_clock capture_pin_edge capture_source_pin capture_source_edge capture_source_insertion_ps launch_clock_pin_arrival_ps capture_clock_pin_arrival_ps'.split()
        for c in ['tt','ff']:
            rows=[]
            for delay,role,slack,la,ca in [('max','setup','7.5','240','230'),('min','hold','3.25','225','245')]:
                rows.append(['ff[0]/Q','ff1/D',delay,'EXACT_STD_PATH','ff[0]/Q','ff1/D',role,slack,'ff[0]/CLK','clk','rise','ck','rise','0','ff1/CLK','clk','rise','ck','rise','0',la,ca])
            (self.out/f'parent_boundary_std_{c}.tsv').write_text('\t'.join(header)+'\n'+''.join('\t'.join(row)+'\n' for row in rows))
            (self.out/f'parent_boundary_std_{c}_counts.tsv').write_text('phase\tORIGINAL_STD_BEFORE_ZERO_UNCERTAINTY\nrelations\t1\nqueries\t2\nerrors\t0\nmissing_paths\t0\nlimited_paths\t0\nnative_engine_cppr_enabled\t0\nadditional_clock_or_cppr_credit\tNONE\n')
            with (self.out/f'export_{c}.log').open('a') as stream:stream.write(f'PARENT_BOUNDARY_STD {c} COMPLETE\n')

    def test_complete_std_evidence_is_not_a_new_qualification(self):
        self.make_exact_parent_std();self.record()
        doc=json.loads((self.out/'child_clock_witness.json').read_text())
        info=doc['corners']['tt']['parent_boundary_relations']['std_path_evidence']
        self.assertEqual(info['paths'],2)
        self.assertEqual(info['additional_clock_or_cppr_credit'],'NONE')
        self.assertEqual(doc['qualification'],'NOT_ASSERTED')

    def test_wrong_std_clock_pin_cannot_join_correct_data_bits(self):
        self.make_exact_parent_std()
        path=self.out/'parent_boundary_std_tt.tsv'
        path.write_text(path.read_text().replace('ff[0]/CLK','wrong/CLK'))
        with self.assertRaisesRegex(ValueError,'clock identities do not match'):
            self.record()

    def test_std_source_must_belong_to_its_actual_clock(self):
        self.make_exact_parent_std()
        path=self.out/'parent_boundary_std_tt.tsv'
        path.write_text(path.read_text().replace('\tck\trise', '\tforeign_root\trise'))
        with self.assertRaisesRegex(ValueError, 'actual source of its clock'):
            self.record()

    def test_unrequested_stale_parent_files_are_ignored(self):
        self.parent_request()
        del self.export['parent_boundary_request']
        self.record()
        doc=json.loads((self.out/'child_clock_witness.json').read_text())
        self.assertNotIn('parent_boundary_relations',doc['corners']['tt'])

    def test_missing_corner_marker_fails(self):
        (self.out / 'export_ff.log').write_text('Tcl Error\n')
        with self.assertRaisesRegex(ValueError, 'incomplete native witness'):
            self.record()

    def test_error_echo_of_marker_cannot_reuse_old_payload(self):
        self.record()
        (self.out/'export_ff.log').write_text('Error while executing "puts OT_CHILD_CLOCK_WITNESS ff COMPLETE"\n')
        with self.assertRaisesRegex(ValueError,'incomplete native witness'):
            self.record()
        self.assertFalse((self.out/'child_clock_witness.json').exists())

    def test_truncated_endpoint_payload_fails_despite_completion_marker(self):
        (self.out / 'child_clock_tt_endpoints.tsv').write_text('reference\tclock_pin\tclock\tlate_ps\tearly_ps\tedge\n')
        with self.assertRaisesRegex(ValueError, 'count mismatch'):
            self.record()

    def test_unknown_pair_endpoint_fails(self):
        p = self.out / 'child_clock_tt_pairs.tsv'
        p.write_text(p.read_text().replace('ff[0]', 'missing_launch'))
        with self.assertRaisesRegex(ValueError, 'endpoint identity missing'):
            self.record()

    def test_missing_clock_source_fails(self):
        p = self.out / 'child_clock_ff_clocks.tsv'
        p.write_text('clock\tsource_kind\tsource\nclk\tvirtual\t\n')
        with self.assertRaisesRegex(ValueError, 'source/root identity'):
            self.record()

    def test_failed_replacement_removes_stale_summary(self):
        self.record()
        (self.out / 'export_ff.log').write_text('incomplete replacement')
        with self.assertRaises(ValueError):
            self.record()
        self.assertFalse((self.out / 'child_clock_witness.json').exists())

    def test_bad_exact_library_identity_fails(self):
        p = self.out / 'child_clock_tt_inputs.tsv'
        p.write_text('constraint\t/native/file.sdc\t' + 'a'*64 + '\n')
        with self.assertRaisesRegex(ValueError, 'library/constraint identities'):
            self.record()


if __name__ == '__main__':
    unittest.main()
