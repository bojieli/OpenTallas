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
 driver [dict create name driver master buf xy {0 0} terms {bufQ}] \
 ff [dict create name DFFHQNx1 block 0] \
 macro [dict create name HARD_CHILD block $::hard_block] \
 buf [dict create name BUFx2 block 0] \
 softCK [dict create inst soft net clock_soft input 1 output 0 mterm CK] \
 softD [dict create inst soft net NULL input 1 output 0 mterm D] \
 softQ [dict create inst soft net direct input 0 output 1 mterm Q] \
 hardCK [dict create inst hard net clock_compensated input 1 output 0 mterm CK] \
 hardD [dict create inst hard net direct input 1 output 0 mterm D] \
 bufQ [dict create inst driver net clock_soft input 0 output 1 mterm Q] \
 CK [dict create name CK] D [dict create name D] Q [dict create name Q] \
 clock_soft [dict create name clock_soft type CLOCK terms {bufQ softCK}] \
 clock_compensated [dict create name clock_compensated type CLOCK terms {hardCK}] \
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
    def run_fixture(self, source, hard=True):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path/'hook.tcl').write_text(source)
            (path/'fixture.tcl').write_text('set hard_block '+str(int(hard))+'\n'+FIXTURE)
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


if __name__ == '__main__':
    unittest.main()
