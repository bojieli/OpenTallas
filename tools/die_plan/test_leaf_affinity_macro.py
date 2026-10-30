"""Exercise the complete F4 affinity hook with DB/STA doubles and a guard mutant."""
from pathlib import Path
import subprocess
import tempfile
import unittest

SOURCE = Path(__file__).with_name('leaf_affinity.tcl')
GUARD = '  if {[[[$it getInst] getMaster] isBlock]} continue\n'
FIXTURE = r'''
namespace eval ord {}
namespace eval sta {}
proc ord::get_db_block {} {return block}
proc ord::get_db_tech {} {return tech}
proc sta::sta_to_db_pin {p} {return $p}
proc all_registers {kind} {
 switch -- $kind {
  -clock_pins {return {softCK hardCK}}
  -data_pins {return {softD hardD}}
  -async_pins {return {}}
  default {error "unexpected register API: $kind"}
 }
}
proc get_property {p property} {if {$property ne "clocks"} {error "unexpected property"}; return clk}
proc get_full_name {p} {return $p}
proc estimate_parasitics {args} {incr ::estimated}
set estimated 0
set moves {}
set db [dict create \
 soft [dict create name soft master ff xy {0 0} terms {softCK softD softQ}] \
 hard [dict create name hard master macro xy {1 0} terms {hardCK hardD}] \
 driver [dict create name driver master buf xy {0 0} terms {bufA bufQ}] \
 driver2 [dict create name driver2 master buf xy {1 0} terms {buf2A buf2Q}] \
 icg0 [dict create name icg0 master icg xy {0 0} terms {icg0Q}] \
 icg1 [dict create name icg1 master icg xy {1 0} terms {icg1Q}] \
 icg [dict create name ICGx1_ASAP7_75t_R block 0] \
 ff [dict create name DFFHQNx1 block 0] \
 macro [dict create name HARD_CHILD block $::hard_block] \
 buf [dict create name BUFx2 block 0] \
 softCK [dict create inst soft net clock_soft input 1 output 0 mterm CK] \
 softD [dict create inst soft net NULL input 1 output 0 mterm D] \
 softQ [dict create inst soft net direct input 0 output 1 mterm Q] \
 hardCK [dict create inst hard net clock_compensated input 1 output 0 mterm CK] \
 hardD [dict create inst hard net direct input 1 output 0 mterm D] \
 bufQ [dict create inst driver net clock_soft input 0 output 1 mterm Q] \
 bufA [dict create inst driver net $::root_a input 1 output 0 mterm A] \
 buf2A [dict create inst driver2 net $::root_b input 1 output 0 mterm A] \
 buf2Q [dict create inst driver2 net clock_compensated input 0 output 1 mterm Q] \
 icg0Q [dict create inst icg0 net gck0 input 0 output 1 mterm Q] \
 icg1Q [dict create inst icg1 net gck1 input 0 output 1 mterm Q] \
 root [dict create name root type CLOCK terms {bufA buf2A}] \
 gck0 [dict create name gck0 type CLOCK terms {icg0Q bufA buf2A}] \
 gck1 [dict create name gck1 type CLOCK terms {icg1Q bufA buf2A}] \
 CK [dict create name CK] D [dict create name D] Q [dict create name Q] A [dict create name A] \
 clock_soft [dict create name clock_soft type CLOCK terms {bufQ softCK}] \
 clock_compensated [dict create name clock_compensated type CLOCK terms {buf2Q hardCK}] \
 direct [dict create name direct type SIGNAL terms {softQ hardD}]]
proc dispatch {self method args} {
 global db moves
 switch -- $method {
  getDbUnitsPerMicron {return 1}
  findNet {return [lindex $args 0]}
  getInst {return [dict get $db $self inst]}
  getMaster {return [dict get $db $self master]}
  getName {return [dict get $db $self name]}
  isBlock {return [dict get $db $self block]}
  getLocation {return [dict get $db $self xy]}
  getITerms {return [dict get $db $self terms]}
  getNet {return [dict get $db $self net]}
  getMTerm {return [dict get $db $self mterm]}
  getSigType {return [dict get $db $self type]}
  isInputSignal {return [dict get $db $self input]}
  isOutputSignal {return [dict get $db $self output]}
  disconnect {dict set db $self net NULL}
  connect {dict set db $self net [lindex $args 0];lappend moves $self}
  default {error "unexpected DB method $self $method"}
 }
}
foreach obj [concat [dict keys $db] {block tech}] {interp alias {} $obj {} dispatch $obj}
source [lindex $argv 0]
puts "FIXTURE hard_clock=[dict get $db hardCK net] moves=$moves estimated=$estimated ck_members=[dict keys $la_ck]"
'''


class HardMacroExclusion(unittest.TestCase):
    def run_fixture(self, source, hard=True, roots=('root','root')):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path/'hook.tcl').write_text(source)
            (path/'fixture.tcl').write_text('set hard_block '+str(int(hard))+'\nset root_a '+roots[0]+'\nset root_b '+roots[1]+'\n'+FIXTURE)
            result = subprocess.run(['tclsh',str(path/'fixture.tcl'),str(path/'hook.tcl')],text=True,capture_output=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            return result.stdout

    def test_compensated_hard_child_never_rehung(self):
        out = self.run_fixture(SOURCE.read_text())
        self.assertIn('hard_clock=clock_compensated moves= estimated=0 ck_members=soft',out)
        self.assertIn('pairs 0',out)

    def test_soft_register_pair_still_uses_affinity(self):
        out = self.run_fixture(SOURCE.read_text(),hard=False)
        self.assertIn('hard_clock=clock_soft moves=hardCK estimated=1',out)
        self.assertIn('pairs 1',out)

    def test_missing_exclusion_mutant_rehangs_macro(self):
        source = SOURCE.read_text()
        self.assertEqual(source.count(GUARD),1)
        out = self.run_fixture(source.replace(GUARD,''))
        self.assertIn('hard_clock=clock_soft moves=hardCK estimated=1',out)
        self.assertNotIn('hard_clock=clock_compensated',out)

    def test_leaves_behind_different_clock_gates_never_merged(self):
        # S81 CRS4 10-29: wc -> epo[s] zero-logic pairs sat behind per-slot ICGs of the same STA clock; re-hanging
        # them onto one gated leaf changed function (post-route LEC NOT EQUIVALENT 44 epo flops).
        out = self.run_fixture(SOURCE.read_text(),hard=False,roots=('gck0','gck1'))
        self.assertIn('hard_clock=clock_compensated moves= estimated=0',out)
        self.assertIn('skip_gate 1',out)

    def test_leaves_behind_same_clock_gate_still_merge(self):
        out = self.run_fixture(SOURCE.read_text(),hard=False,roots=('gck0','gck0'))
        self.assertIn('hard_clock=clock_soft moves=hardCK estimated=1',out)
        self.assertIn('skip_gate 0',out)

    def test_missing_gate_guard_mutant_crosses_gates(self):
        source = SOURCE.read_text()
        guard = '  if {$la_gx} { incr la_skip_gate; continue }\n'
        self.assertEqual(source.count(guard),1)
        out = self.run_fixture(source.replace(guard,''),hard=False,roots=('gck0','gck1'))
        self.assertIn('hard_clock=clock_soft moves=hardCK estimated=1',out)


if __name__ == '__main__':
    unittest.main()
