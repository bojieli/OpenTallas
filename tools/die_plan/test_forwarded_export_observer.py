import csv
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
import forwarded_export_observer as F

REQ=dict(master_clock='clk',native_output_clock='vclk',roots=['rootA','rootB'],exports=[dict(export='fclk_out_data',source='rootA',bits=['data[0]','data[1]','data[2]'])])
FAKE=r'''
namespace eval sta {
 proc get_port_pin {x} {return $x}
 proc worst_slack_cmd {x} {return 0}
}
proc write_sdc {path} {set f [open $path w];puts $f {set_clock_uncertainty 25 -hold [all_clocks]};close $f}
proc get_full_name {x} {return $x}
proc get_clocks {args} {return [lindex $args end]}
proc clk {method} {if {$method eq "waveform"} {return {0 4.165e-10}};if {$method eq "period"} {return 8.33e-10}}
proc fclk_out_data {method} {
 if {$method eq "is_generated"} {return [expr {![info exists ::bad_generated]}]}
 if {$method eq "period"} {return 8.33e-10}
 if {$method eq "waveform"} {return {0 4.165e-10}}
 if {$method eq "vertices"} {return kvertex}
}
proc get_ports {args} {
 set pattern [lindex $args end];set out {}
 foreach value {{data[0]} {data[1]} {data[2]} data0 fclk_out_data} {if {[regexp $pattern $value]} {lappend out $value}}
 return $out
}
proc get_cells {args} {set p [lindex $args end];return [lindex [split $p /] 0]}
proc all_registers {args} {return {ff0/CLK ff1/CLK ff2/CLK}}
proc get_property {object field} {
 if {$object eq "clk" && $field eq "sources"} {return {rootA rootB}}
 if {$object eq "pe"} {
  switch $field {
   startpoint {return "ff$::idx/Q"}
   endpoint {return "data\[$::idx\]"}
   points {return point}
   slack {return [expr {$::delay eq "min" ? 4.0 : 9.0}]}
  }
 }
 if {$object eq "point" && $field eq "arrival"} {return [expr {$::delay eq "min" ? 110.0+$::idx : 250.0+$::idx}]}
 error "unknown fake property $object $field"
}
proc find_timing_paths {args} {
 set port [lindex $args [expr {[lsearch -exact $args -to]+1}]]
 regexp {\[([0-9]+)\]} $port -> ::idx
 set ::delay [lindex $args [expr {[lsearch -exact $args -path_delay]+1}]]
 if {[info exists ::no_path]} {return {}}
 return pe
}
proc pe {method} {if {$method eq "path"} {return dp};if {$method eq "target_clk"} {return vclk};error unknownPathEndMethod}
proc dp {method} {
 set source [expr {$::idx==1 ? "rootB" : "rootA"}]
 if {[info exists ::foreign]} {set source foreignRoot}
 return [list a b c clk ^ clk_src $source]
}
proc ot_ps_source_from_tag {tag clock which} {
 set source [lindex $tag end]
 if {$source ni {rootA rootB}} {error foreignActualRoot}
 return [list $source [expr {[lindex $tag 4] eq "^" ? "rise" : "fall"}] 0]
}
proc kvertex {method edge which} {set ::ke $edge;set ::kw $which;set ::ki 0;return kit}
proc kit {method} {
 if {$method eq "has_next"} {return [expr {$::ki==0}]}
 if {$method eq "next"} {incr ::ki;return kpath}
 if {$method eq "finish"} {return}
}
proc kpath {method} {
 if {$method eq "arrival"} {return [expr {(($::ke eq "fall" ? 416.5 : 0)+($::kw eq "min" ? -120 : 20))*1e-12}]}
 return [list a b c clk [expr {$::ke eq "rise" ? "^" : "v"}] {(clock prop)} clk_src rootA]
}
'''

class Observer(unittest.TestCase):
 def run_tcl(self,prefix='',limit=6):
  tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);p=Path(tmp.name)
  text=FAKE+'\n'+prefix+'\n'+F.emit(REQ,p,limit,True,helpers=False)
  script=p/'observer.tcl';script.write_text(text)
  r=subprocess.run(['tclsh',str(script)],capture_output=True,text=True)
  self.assertEqual(r.returncode,0,r.stderr)
  log=p/'log';log.write_text(r.stdout)
  return p,log,r.stdout
 def test_generated_mixed_owner_all_bits_and_uncredited_bounds(self):
  p,log,_=self.run_tcl();v=F.validate(REQ,p,log)
  self.assertEqual(v['actual_launch_roots'],['rootA','rootB'])
  self.assertEqual(v['bits'],3);self.assertEqual(v['qualification'],'NOT_ASSERTED')
  rows=list(csv.DictReader((p/'data_k.tsv').open(),delimiter='\t'))
  self.assertEqual({r['data_bit'] for r in rows},set(REQ['exports'][0]['bits']))
  self.assertTrue(all(r['native_std_target_clock']=='vclk' for r in rows))
  self.assertAlmostEqual(float(rows[0]['uncredited_relative_bound_ps']),90)
 def test_foreign_actual_root_fails_requested_observation(self):
  p,log,_=self.run_tcl('set ::foreign 1')
  with self.assertRaisesRegex(ValueError,'missing/error'):F.validate(REQ,p,log)
 def test_declared_forward_source_must_match_actual_clock_path(self):
  tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);p=Path(tmp.name)
  req=json.loads(json.dumps(REQ));req['exports'][0]['source']='rootB'
  script=p/'observer.tcl';script.write_text(FAKE+'\n'+F.emit(req,p,6,True,helpers=False))
  r=subprocess.run(['tclsh',str(script)],capture_output=True,text=True)
  self.assertEqual(r.returncode,0,r.stderr)
  self.assertIn('physical source differs',r.stdout)
  log=p/'log';log.write_text(r.stdout)
  with self.assertRaisesRegex(ValueError,'incomplete'):F.validate(req,p,log)

 def test_bounded_no_path_and_generated_missing_fail_clearly(self):
  for prefix,limit in [('',1),('set ::no_path 1',6),('set ::bad_generated 1',6)]:
   p,log,_=self.run_tcl(prefix,limit)
   with self.assertRaises(ValueError):F.validate(REQ,p,log)
 def test_default_off_literal_names_and_no_constraint_mutation(self):
  self.assertNotIn('find_timing_paths',F.emit(REQ,'/tmp/out'))
  active=F.emit(REQ,'/tmp/out',6,True,helpers=False)
  for command in ('set_clock_uncertainty','set_clock_latency','set_output_delay','delete_clock','ot_ps_zero_unc'):
   self.assertNotIn(command,active)
  self.assertIn('ORIGINAL_CONSTRAINED_STD_BEFORE_ZERO_UNC',active)
  p,log,_=self.run_tcl();F.validate(REQ,p,log) # pool includes data0; exact data[0] must not alias it
 def test_request_binds_actual_generated_source_and_compiled_width(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t);s=p/'sdc';n=p/'net.v'
   s.write_text('create_clock -name clk -period 833 [get_ports {rootA rootB}]\ncreate_generated_clock -name fclk_out_data -master_clock clk -source [get_ports rootA] -divide_by 1 [get_ports fclk_out_data]\n')
   n.write_text('module top(data);\noutput [2:0] data;\nendmodule\n')
   r=F.request(s,n,'top');self.assertEqual(r['exports'][0]['bits'],REQ['exports'][0]['bits'])
   s.write_text(s.read_text().replace('source [get_ports rootA]','source [get_ports foreignRoot]'))
   with self.assertRaisesRegex(ValueError,'foreign'):F.request(s,n,'top')
if __name__=='__main__':unittest.main()
