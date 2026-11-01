import csv
from pathlib import Path
import subprocess
import tempfile
import unittest
import parent_boundary as PB
import signoff

FAKE = r'''
namespace eval sta {proc crpr_enabled {} {return 0}}
proc get_full_name {x} {return $x}
proc fake_exact {args} {
 set value [lindex $args end]
 if {[lsearch -exact $args -regexp]>=0} {
  set value [string range $value 1 end-1]
  regsub -all {\\(.)} $value {\1} value
 }
 return $value
}
proc get_cells {args} {return [fake_exact {*}$args]}
proc get_pins {args} {
 if {[lindex $args 0] eq "-of_objects"} {return {h0/in h0/out0 h0/out1}}
 return [fake_exact {*}$args]
}
proc get_property {x field} {
 if {$field eq "ref_name"} {return ot_s81ph_native_sel_hist_bank}
 if {$field eq "direction"} {return [expr {$x eq "h0/in" ? "input" : "output"}]}
 if {$field eq "clocks"} {return clk}
 if {$x eq "clk" && $field eq "sources"} {return {root0 root1}}
 if {$x eq "pe" && $field eq "startpoint"} {return $::sp}
 if {$x eq "pe" && $field eq "endpoint"} {return $::dp}
 if {$x eq "pe" && $field eq "slack"} {return [expr {$::delay eq "max" ? 7.5 : 3.25}]}
 error "unsupported test property $x $field"
}
proc ot_ps_clock_role {pin role} {
 if {$role eq "clkq" && $pin in {ff/Q h0/out0 h0/out1}} {
  return [list [expr {$pin eq "ff/Q" ? "ff/CLK" : "h0/CLK"}] rise]
 }
 if {$role in {setup hold} && $pin in {h0/in cap/D}} {
  return [list [expr {$pin eq "h0/in" ? "h0/CLK" : "cap/CLK"}] rise]
 }
 return {}
}
proc get_fanin {args} {return ff/Q}
proc get_fanout {args} {return cap/D}
proc find_timing_paths {args} {
 set ::sp [lindex $args [expr {[lsearch -exact $args -from]+1}]]
 set ::dp [lindex $args [expr {[lsearch -exact $args -to]+1}]]
 set ::delay [lindex $args [expr {[lsearch -exact $args -path_delay]+1}]]
 if {[info exists ::no_path] && $::no_path} {return {}}
 return pe
}
proc pe {method} {
 switch $method {
  is_check {return 1} is_latch_check {return 0}
  check_role {return [expr {$::delay eq "max" ? "setup" : "hold"}]}
  path {return launch_path} target_clk_path {return capture_path}
 }
 error "unsupported PathEnd method"
}
proc launch_path {method} {return {a b c clk ^ clk_src root1}}
proc capture_path {method} {return {a b c clk ^ clk_src root0}}
proc get_clocks {args} {return clk}
proc clk {method} {return {0 4.165e-10}}
foreach name {ff/CLK h0/CLK cap/CLK} {proc $name {method} {return vertex}}
proc vertex {method args} {set ::clock_iter 0;return clock_it}
proc clock_it {method} {
 switch $method {
  has_next {return [expr {$::clock_iter<2}]}
  next {set id $::clock_iter;incr ::clock_iter;return clock_path$id}
  finish {return}
 }
}
proc clock_path0 {method} {
 if {$method eq "arrival"} {return 3e-12}
 return {a b c clk ^ {(clock prop)} clk_src root0}
}
proc clock_path1 {method} {
 if {$method eq "arrival"} {return 9e-12}
 return {a b c clk ^ {(clock prop)} clk_src root1}
}
proc ot_ps_source_from_tag {tag clock which} {
 set source [lindex $tag end]
 if {[info exists ::bad_source] && $::bad_source} {error "ambiguous actual source tag"}
 if {$source ni {root0 root1}} {error "unknown actual source"}
 return [list $source rise [expr {$source eq "root1" ? 3.0 : 1.0}]]
}
'''


class ParentObserver(unittest.TestCase):
    def run_observer(self, limit=100, prefix=''):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        root=Path(temp.name)
        body=PB.std_tcl(['h0'],limit,'tt').replace('/out/',str(root)+'/')
        script=root/'observer.tcl';script.write_text(FAKE+'\n'+prefix+'\n'+body)
        result=subprocess.run(['tclsh',str(script)],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        with (root/'parent_boundary_std_tt.tsv').open() as stream:
            rows=list(csv.DictReader(stream,delimiter='\t'))
        return rows,(root/'parent_boundary_std_tt_counts.tsv').read_text(),result.stdout

    def test_nested_bus_instance_lookup_is_anchored_and_literal(self):
        body=PB.std_tcl(['h0'],1,'tt')
        proc=body[body.index('proc pb_exact'):body.index('proc pb_pin')]
        query=proc+'\nset name {u_q.u_s.g_bank[0].u_bank/out[17]}\nputs [regexp [pb_exact $name] $name]\nputs [regexp [pb_exact $name] {u_qXu_sXg_bank0Xu_bank/out17}]\n'
        result=subprocess.run(['tclsh'],input=query,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(result.stdout.splitlines(),['1','0'])

    def test_exact_data_bits_and_actual_multisource_tags_survive(self):
        rows,counts,_=self.run_observer()
        self.assertEqual(len(rows),6)
        self.assertTrue(all(row['status']=='EXACT_STD_PATH' for row in rows))
        self.assertEqual({r['launch_data_pin'] for r in rows},{'ff/Q','h0/out0','h0/out1'})
        self.assertTrue(all(r['launch_source_pin']=='root1' and r['capture_source_pin']=='root0' for r in rows))
        self.assertTrue(all(float(r['launch_clock_pin_arrival_ps'])==9.0 and float(r['capture_clock_pin_arrival_ps'])==3.0 for r in rows))
        self.assertEqual({r['native_std_slack_ps'] for r in rows},{'7.5','3.25'})
        self.assertIn('ORIGINAL_STD_BEFORE_ZERO_UNCERTAINTY',counts)
        self.assertIn('additional_clock_or_cppr_credit\tNONE',counts)

    def test_no_path_is_not_a_clock_bound_disguised_as_slack(self):
        rows,counts,_=self.run_observer(prefix='set ::no_path 1')
        self.assertTrue(all(r['status']=='NO_PATH' and not r['native_std_slack_ps'] for r in rows))
        self.assertIn('missing_paths\t6',counts)

    def test_budget_and_ambiguous_source_are_explicit(self):
        rows,counts,log=self.run_observer(limit=1,prefix='set ::bad_source 1')
        self.assertEqual([r['status'] for r in rows].count('ERROR'),1)
        self.assertEqual([r['status'] for r in rows].count('LIMIT'),5)
        self.assertIn('ambiguous actual source tag',log)
        self.assertTrue(all(not r['native_std_slack_ps'] for r in rows))

    def test_original_std_observer_is_outside_procedure_and_before_zero_unc(self):
        text=signoff.session_tcl('tt',[],True,retain_child_clock_witness=True,
            parent_boundary_instances=['h0'],parent_boundary_std_limit=100)
        at=text.index('unset ::ot_ps_lib_only\n')
        observer=text.index('set ::pb_targets',at)
        zero=text.index('ot_ps_zero_unc\n',observer)
        self.assertLess(at,observer);self.assertLess(observer,zero)
        plain=signoff.session_tcl('tt',[],True)
        self.assertNotIn('set ::pb_targets',plain)
        no_slack=signoff.session_tcl('tt',[],True,retain_child_clock_witness=True,parent_boundary_instances=['h0'])
        self.assertNotIn('set ::pb_targets',no_slack)
        self.assertIn('set ::ot_ps_parent_targets [list {h0}]',no_slack)

    def test_actual_native_pair_loop_keeps_two_output_bits_before_clock_dedup(self):
        root=Path(__file__).resolve().parent
        body=(root/'pair_skew.tcl').read_text()
        script=r"""
set ::ot_ps_lib_only 1
"""+body+r"""
proc get_full_name {x} {return $x}
proc all_registers {kind} {if {$kind eq "-async_pins"} {return {}};return c/D}
proc get_fanin {args} {return {h0/out0 h0/out1}}
proc ot_ps_clock_role {pin role} {
 if {$role eq "setup"} {return {c/CS rise}}
 if {$role eq "hold"} {return {c/CH fall}}
 return {h0/CLK rise}
}
proc ot_ps_add_clock {pin edge} {
 if {$pin eq "c/CS"} {return cs}
 if {$pin eq "c/CH"} {return ch}
 return h0
}
set ::ot_ps_R [dict create h0 {h0/CLK clk 10 9 rise} cs {c/CS clk 12 11 rise} ch {c/CH clk 13 12 fall}]
set ::ot_ps_parent_targets {h0}
lassign [ot_ps_related $::ot_ps_R] P np nx nd
if {$np != 1 || [dict size $::ot_ps_parent_relations] != 2} {error "lost exact macro output bit identities"}
set outputs {};dict for {k row} $::ot_ps_parent_relations {lappend outputs [lindex $row 0]}
if {[lsort $outputs] ne {h0/out0 h0/out1}} {error "wrong exact output identities"}
puts NATIVE_INTERFACE_IDENTITY_PASS
"""
        result=subprocess.run(['tclsh'],input=script,text=True,capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('NATIVE_INTERFACE_IDENTITY_PASS',result.stdout)

    def test_exact_instance_names_only(self):
        for names in [[],['h*'],['h0','h0'],['bad\nname']]:
            with self.assertRaises(ValueError):PB.targets_tcl(names)


if __name__=='__main__':unittest.main()
