"""Clock-source measurement must follow physical CTS, including recreated clocks."""
import pathlib
import subprocess
import sys
import unittest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import ref_tile as RT

class PreCtsStage(unittest.TestCase):
    def test_generator_stage_and_last_propagation(self):
        s={'name':'stage','clock_port':'ck','sdc_extra':[]}
        self.assertLess(RT.gen_sdc(s,770).index('set ::ot_ref_pre_cts 1'), RT.gen_sdc(s,770).index('create_clock'))
        signoff=RT.gen_signoff(s,'*','none_*')
        self.assertLess(signoff.index('set ::ot_ref_pre_cts 0'), signoff.index('create_clock'))
        self.assertTrue(signoff.endswith('set_propagated_clock [all_clocks]\n'))

    def test_hend_pre_cts_never_propagates_or_measures_and_post_cts_does(self):
        root=pathlib.Path(RT.ROOT)/'physical/s81_die_views/hend/negcap'
        harness=r'''
namespace eval sta {}
proc unknown {args} {return {}}
proc get_clocks {args} {return [lindex $args end]}
proc get_ports {args} {if {[lindex $args end] eq "fi*"} {return fi0};return [lindex $args end]}
proc get_property {obj key} {if {$key eq "period"} {return 770};return $obj}
proc set_propagated_clock {args} {incr ::propagated}
proc report_clock_latency {args} {incr ::measured}
proc sta::redirect_string_begin {} {}
proc sta::redirect_string_end {} {return "rise -> rise 100 120 latency"}
set propagated 0
set measured 0
'''
        for path in root.glob('*.sdc'):
            for before in (0,1):
                with self.subTest(file=path.name, before=before):
                    script=harness+f'\nset ::ot_ref_pre_cts {before}\n'+path.read_text()+f'\nif {{$propagated != {0 if before else 1}}} {{error "propagation stage wrong"}}\n'+ ('if {$measured != 0} {error "preCTS clock phase measured"}\n' if before else 'if {$measured < 2} {error "both CTS domains not measured"}\n')+'puts PASS\n'
                    run=subprocess.run(['tclsh'],input=script,text=True,capture_output=True)
                    self.assertEqual(run.stderr,'')
                    self.assertIn('PASS',run.stdout)

if __name__=='__main__': unittest.main()
