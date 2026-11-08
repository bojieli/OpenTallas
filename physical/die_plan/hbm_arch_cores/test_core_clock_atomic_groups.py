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
 def test_collapse_split_leaf_then_receipt(self):
  # DIE-HEAD-85: CTS L1 split of a small atomic tap net (two sibling BUF leaves + a dummy) is re-hung on the majority
  # leaf, the emptied sibling + dummy are deleted, and dt_atomic_check then passes; negative controls stay errors.
  script='source {'+str(HERE/'core_clock_atomic_groups.tcl')+'}\n'+r'''
proc object {id method args} {
 global objects destroyed
 switch $method {
  findInst - findITerm - findNet {
   set key [lindex $args 0]
   if {![dict exists $objects $id $method $key]} {return NULL}
   set v [dict get $objects $id $method $key]
   if {$v in $destroyed} {return NULL}
   return $v
  }
  getName { if {[dict exists $objects $id getName]} {return [dict get $objects $id getName]}; return $id }
  disconnect { dict set objects $id getNet NULL; return }
  connect { dict set objects $id getNet [lindex $args 0]; return }
  getITerms {
   if {[dict exists $objects $id getITerms]} {return [dict get $objects $id getITerms]}
   set r {}
   dict for {k v} $objects { if {[dict exists $v getNet] && [dict get $v getNet] eq $id && [dict get $v getInst] ni $destroyed} {lappend r $k} }
   return $r
  }
 }
 return [dict get $objects $id $method]
}
namespace eval odb {}
proc odb::dbInst_destroy {i} { lappend ::destroyed $i }
proc odb::dbNet_destroy {n} { lappend ::destroyed $n }
set destroyed {}
set objects [dict create \
 block {findInst {a ia b ib c ic} findNet {leafA leafA leafB leafB root root}} \
 ia {findITerm {CLK pa} getLocation {0 0} getMaster ffm} \
 ib {findITerm {CLK pb} getLocation {1 0} getMaster ffm} \
 ic {findITerm {CLK pc} getLocation {2 0} getMaster ffm} \
 pa {getNet leafA isInputSignal 1 isOutputSignal 0 getInst ia getMTerm clock_input} \
 pb {getNet leafA isInputSignal 1 isOutputSignal 0 getInst ib getMTerm clock_input} \
 pc {getNet leafB isInputSignal 1 isOutputSignal 0 getInst ic getMTerm clock_input} \
 pyA {getNet leafA isInputSignal 0 isOutputSignal 1 getInst bufA getMTerm signal_output} \
 piA {getNet root isInputSignal 1 isOutputSignal 0 getInst bufA getMTerm signal_input} \
 pyB {getNet leafB isInputSignal 0 isOutputSignal 1 getInst bufB getMTerm signal_output} \
 piB {getNet root isInputSignal 1 isOutputSignal 0 getInst bufB getMTerm signal_input} \
 pdA {getNet leafB isInputSignal 1 isOutputSignal 0 getInst dum getMTerm signal_input} \
 pdY {getNet NULL isInputSignal 0 isOutputSignal 1 getInst dum getMTerm signal_output} \
 bufA {getMaster bufm getLocation {0 0} getITerms {piA pyA}} \
 bufB {getMaster bufm getLocation {2 0} getITerms {piB pyB}} \
 dum {getMaster invm getLocation {3 0} getITerms {pdA pdY}} \
 ffm {getName DFFHQNx1_ASAP7_75t_R} bufm {getName BUFx4_ASAP7_75t_R} invm {getName INVx1_ASAP7_75t_R} \
 clock_input {getIoType INPUT getSigType CLOCK} signal_input {getIoType INPUT getSigType SIGNAL} \
 signal_output {getIoType OUTPUT getSigType SIGNAL} \
 leafA {getBTerms {}} leafB {getBTerms {}} \
 root {getBTerms {port}} port {getIoType INPUT getName clk}]
dict for {id v} $objects {interp alias {} $id {} object $id}
set baseline $objects
set g {{g0 {a b c}}}
if {![catch {dt_atomic_check block $g 4 5 clk}]} {error "split must fail before collapse"}
set r [dt_atomic_collapse block $g]
if {$r ne {1 1 1 1}} {error "counts $r"}
if {[pc getNet] ne "leafA" || "bufB" ni $destroyed || "dum" ni $destroyed || "leafB" ni $destroyed} {error "rehang/delete"}
if {[dt_atomic_check block $g 4 5 clk] != 1} {error "receipt after collapse"}
foreach mutation {notsibling realload invbuf} {
 set objects $baseline; set destroyed {}
 switch $mutation {
  notsibling {dict set objects piB getNet other_root}
  realload {dict set objects dum getMaster ffm}
  invbuf {dict set objects bufB getMaster invm}
 }
 if {![catch {dt_atomic_collapse block $g}]} {error "missed $mutation"}
}
set objects $baseline; set destroyed {}
if {[dt_atomic_collapse block {{g0 {a b}}}] ne {0 0 0 0}} {error "one-leaf group must be untouched"}
puts PASS
'''
  r=subprocess.run(['tclsh'],input=script,text=True,capture_output=True)
  self.assertEqual(r.stderr,'');self.assertIn('PASS',r.stdout)
 def test_generated_post_cts_collapses_before_receipt(self):
  src=(HERE/'gen_core_kit_hbm.py').read_text()
  i=src.index('{dt_atomic_collapse [ord::get_db_block] $groups}');j=src.index('"dt_atomic_check [ord::get_db_block] $groups')
  self.assertLess(i,j);self.assertIn('OT_DTAP_ATOMIC_COLLAPSE',src[i-300:i])
if __name__=='__main__':unittest.main()
