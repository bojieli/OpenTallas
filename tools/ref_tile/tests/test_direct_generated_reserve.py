"""Direct D4/E2 budgets follow actual generated-clock ancestry."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import test_generated_clock_family as G
import clock_entry_constraints as CE

FIXTURE=Path(__file__).with_name('generated_clock_family')
RECORD=dict(D=4,E=2,landings=[dict(name='0')],landing_implementation=dict(direct_quarter_period_timing=True,chunk_bits=24))

INIT=r'''
delete_clock [all_clocks]
create_clock -name core_clk -period 100
create_clock -name ot_entry_0 -period 100 [get_ports ck]
create_clock -name ot_entry_1 -period 100 [get_ports other]
'''
GENERATED=r'''
create_generated_clock -name bank -source [get_ports ck] -master_clock ot_entry_0 -edges {3 4 11} [get_pins b1/Y]
create_generated_clock -name nested -source [get_pins b1/Y] -master_clock bank -divide_by 1 [get_pins b2/Y]
create_generated_clock -name otherbank -source [get_ports other] -master_clock ot_entry_1 -divide_by 4 [get_pins fo/CK]
'''
BASE=r'''
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
set_propagated_clock [all_clocks]
ot_cf_refresh
proc canonical {} {
 write_sdc /tmp/direct-constraints.sdc
 set fd [open /tmp/direct-constraints.sdc];set text [read $fd];close $fd
 set rows {}
 foreach line [split $text \n] {if {![string match {#*} $line]} {lappend rows $line}}
 return [join $rows \n]
}
proc pair_rows {text from to} {
 set rows {}
 foreach line [split $text \n] {
  if {![string match {set_clock_uncertainty *} $line]} continue
  foreach fr {rise fall} {
   foreach tr {rise fall} {
    if {[string first [format {-%s_from [get_clocks {%s}]} $fr $from] $line] >= 0 &&
        [string first [format {-%s_to [get_clocks {%s}]} $tr $to] $line] >= 0} {lappend rows $line}
   }
  }
 }
 return $rows
}
proc assert_pair {text from to setup hold} {
 set rows [pair_rows $text $from $to]
 if {[llength $rows] != 8} {error "missing rise/fall direct guards $from -> $to: $rows"}
 foreach line $rows {
  set want [expr {[string first {-setup } $line] >= 0 ? $setup : $hold}]
  if {![regexp { ([-+0-9.eE]+)$} $line -> value]} {error "missing native uncertainty value $line"}
  if {abs($value-$want)>0.001} {error "weakened direct guard $line expected $want"}
 }
}
'''

class DirectGeneratedReserve(unittest.TestCase):
    def direct(self,residual=150):
        with patch.object(CE,'landed_record',return_value=RECORD):
            return CE.landed_sdc(dict(landed_record='fixture',landing_direct_residual_ps=residual),'.')

    def test_default_sdc_is_byte_identical_to_609(self):
        rec=dict(RECORD,landing_implementation=dict(direct_quarter_period_timing=False,chunk_bits=24))
        with patch.object(CE,'landed_record',return_value=rec):
            text=CE.landed_sdc(dict(landed_record='fixture',landing_direct_residual_ps=150),'.')
        self.assertEqual(text,(FIXTURE/'legacy_default_d4e2.sdc').read_text())

    def test_ordinary_direct_effective_constraints_are_byte_identical(self):
        legacy=(FIXTURE/'legacy_direct_d4e2.sdc').read_text()
        script=INIT+BASE+legacy+'\nset previous [canonical]\n'+self.direct()+r'''
if {[canonical] ne $previous} {error "ordinary direct effective SDC changed"}
'''
        helper=G.GeneratedClockFamily()
        helper.assert_native_pass(helper.native(script))

    def test_all_actual_descendants_keep_stronger_direct_reserves(self):
        script=INIT+GENERATED+BASE
        for residual in (150,225):
            script+=self.direct(residual)
            script+=f'\nset text [canonical]\nset expected_setup {60+residual+75}\nset expected_hold {25+residual}\n'
            script+=r'''
foreach a {ot_entry_0 bank nested} {
 foreach b {ot_entry_1 otherbank} {
  assert_pair $text $a $b $expected_setup $expected_hold
  assert_pair $text $b $a $expected_setup $expected_hold
 }
}
foreach pair {{ot_entry_0 bank} {bank nested} {nested ot_entry_0} {ot_entry_1 otherbank}} {
 lassign $pair a b
 if {[llength [pair_rows $text $a $b]] || [llength [pair_rows $text $b $a]]} {error "same-family semantics changed $a/$b"}
}
'''
        helper=G.GeneratedClockFamily()
        helper.assert_native_pass(helper.native(script))

if __name__=='__main__':unittest.main()
