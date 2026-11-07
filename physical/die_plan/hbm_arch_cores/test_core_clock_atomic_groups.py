"""Atomic short-chain branches: explicit membership, budgets and default-off behavior."""
import importlib.util
from pathlib import Path
import json, subprocess, tempfile, unittest
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('atomic_core_gen', HERE/'gen_core_kit_hbm.py')
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
class Groups(unittest.TestCase):
 def manifest(self, **kw):
  return dict(schema='opentallas.core_atomic_clock_groups.v1',module='tx',max_sinks=16,max_radius_um=20,groups=[dict(name='shift0',members=[r'u_enc.d0\[0\]$_DFF_P_',r'u_enc.d1\[0\]$_DFF_P_'])],**kw)
 def run_manifest(self,d,clocks=('clk',),taps='density'):
  with tempfile.TemporaryDirectory() as x:
   p=Path(x)/'m.json';p.write_text(json.dumps(d));return m.atomic_clock_groups(p,'tx',clocks,taps)
 def test_exact_roundtrip_dollar_and_brackets(self):
  d,t=self.run_manifest(self.manifest())
  script='set groups {'+t+'}\nputs [lindex [lindex $groups 0] 1]\n'
  out=subprocess.run(['tclsh'],input=script,text=True,capture_output=True,check=True).stdout
  self.assertIn(r'u_enc.d0\[0\]$_DFF_P_',out)
 def test_reject_overlap(self):
  d=self.manifest();d['groups'].append(dict(name='other',members=d['groups'][0]['members']))
  with self.assertRaises(ValueError):self.run_manifest(d)
 def test_reject_multiroot_or_no_density(self):
  for c,t in [(('a','b'),'density'),(('clk',),'off')]:
   with self.assertRaises(ValueError):self.run_manifest(self.manifest(),c,t)
 def test_reject_empty_singleton_overcap(self):
  for n in [0,1,17]:
   d=self.manifest();d['groups'][0]['members']=[f'ff{i}' for i in range(n)]
   with self.assertRaises(ValueError):self.run_manifest(d)
 def test_reject_unsafe_name(self):
  d=self.manifest();d['groups'][0]['members'][0]='bad{member'
  with self.assertRaises(ValueError):self.run_manifest(d)
 def test_pure_planner_and_negative_controls(self):
  script='source {'+str(HERE/'core_clock_atomic_groups.tcl')+'}\n'+r'''
set p [dict create a {0 0 ia} b {2 0 ib} c {10 0 ic} d {12 0 id} free {8 8 iff}]
set r [dt_atomic_plan $p {{g0 {a b}} {g1 {c d}}} 2 3]
if {[dict size [dict get $r pinned]] != 4 || [llength [dict get $r sets]] != 2 || [llength [dict get $r rest]] != 1} {error "membership"}
foreach bad {{{g0 {a missing}}} {{g0 {a b}} {g1 {b c}}} {{g0 {a b c}}} {{g0 {a d}}}} {
 if {![catch {dt_atomic_plan $p $bad 2 3}]} {error "missed negative control"}
}
puts PASS
'''
  r=subprocess.run(['tclsh'],input=script,text=True,capture_output=True)
  self.assertEqual(r.stderr,'');self.assertIn('PASS',r.stdout)
 def test_actual_leaf_receipt_negative_controls(self):
  script='source {'+str(HERE/'core_clock_atomic_groups.tcl')+'}\n'+r'''
proc object {id method args} {
 set d [dict get $::objects $id]
 if {$method in {findInst findITerm}} {
  set key [lindex $args 0]
  if {![dict exists $d $method $key]} {return NULL}
  return [dict get $d $method $key]
 }
 return [dict get $d $method]
}
set objects [dict create \
 block {findInst {a ia b ib}} \
 ia {findITerm {CLK pa} getLocation {0 0}} \
 ib {findITerm {CLK pb} getLocation {1 0}} \
 pa {getNet leaf isInputSignal 0 isOutputSignal 0 getInst ia getMTerm clock_input} \
 pb {getNet leaf isInputSignal 0 isOutputSignal 0 getInst ib getMTerm clock_input} \
 py {getNet leaf isInputSignal 0 isOutputSignal 1 getInst buf getMTerm signal_output} \
 pi {getNet root isInputSignal 1 isOutputSignal 0 getInst buf} \
 buf {getMaster master getLocation {0 0} getITerms {pi py}} \
 clock_input {getIoType INPUT getSigType CLOCK} \
 signal_output {getIoType OUTPUT getSigType SIGNAL} \
 master {getName BUFx24_ASAP7_75t_R} \
 leaf {getITerms {pa pb py} getBTerms {}} \
 root {getITerms {pi} getBTerms {port}} \
 port {getIoType INPUT getName clk}]
dict for {id v} $objects {interp alias {} $id {} object $id}
set baseline $objects
if {[dt_atomic_check block {{g0 {a b}}} 2 3 clk] != 1} {error "positive"}
foreach mutation {split invert far root overcap missing} {
 set objects $baseline
 switch $mutation {
  split {dict set objects pb getNet other_leaf}
  invert {dict set objects master getName INVx1}
  far {dict set objects ib getLocation {100 100}}
  root {dict set objects port getName other_clk}
  missing {dict set objects block findInst b NULL}
 }
 set cap [expr {$mutation eq "overcap" ? 1 : 2}]
 if {![catch {dt_atomic_check block {{g0 {a b}}} $cap 3 clk}]} {error "missed $mutation"}
}
puts PASS
'''
  r=subprocess.run(['tclsh'],input=script,text=True,capture_output=True)
  self.assertEqual(r.stderr,'');self.assertIn('PASS',r.stdout)
if __name__=='__main__':unittest.main()
