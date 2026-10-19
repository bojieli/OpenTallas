"""Native OpenSTA regression: physical generated-family ownership and phase.

Run on the fleet with OT_NATIVE_CLOCK_FAMILY=1. This is a source/STA mechanism
probe; LAND's joined all-K phase and post-CTS qualification remain separate.
"""
import os
from pathlib import Path
import subprocess
import tempfile
import sys
import importlib.util
import shutil
import unittest

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = Path(__file__).with_name('generated_clock_family')
SHARED = ROOT / 'physical/common_flow/clock_family.tcl'

class GeneratedClockFamily(unittest.TestCase):
    def test_routed_copy_is_identical(self):
        io = (ROOT / 'physical/common_flow/io_ref_routed.sdc').read_text()
        self.assertEqual(io.split('# BEGIN shared clock_family.tcl (checked byte-for-byte by tests)\n')[1].split('# END shared clock_family.tcl')[0], SHARED.read_text())

    def test_flat_route_helper_packaging(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)
            shutil.copy(ROOT/'tools/closure_loop/ck_insertion.py', p/'ck_insertion.py')
            shutil.copy(SHARED, p/'clock_family.tcl')
            spec=importlib.util.spec_from_file_location('flat_ck_insertion',p/'ck_insertion.py')
            module=importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self.assertEqual(module.CLOCK_FAMILY_TCL, SHARED.read_text())

    def native(self, extra='', edges='3 4 11', pre=''):
        if os.environ.get('OT_NATIVE_CLOCK_FAMILY') != '1':
            self.skipTest('native probe requires fleet Docker/OpenSTA')
        with tempfile.TemporaryDirectory(dir=FIXTURE) as td:
            p = Path(td)
            script = f'''read_liberty /fixture/toy.lib
read_verilog /fixture/toy.v
link_design top
create_clock -name root -period 100 -waveform {{10 60}} [get_ports ck]
create_clock -name other -period 100 [get_ports other]
create_generated_clock -name bank -source [get_ports ck] -master_clock root -edges {{{edges}}} [get_pins b1/Y]
set_propagated_clock [all_clocks]
{pre}
source /shared/clock_family.tcl
proc assert_close {{actual expected}} {{if {{abs($actual-$expected)>0.001}} {{error "expected $expected got $actual"}}}}
ot_cf_refresh
{extra}
puts PASS
exit
'''
            # OpenSTA reports Tcl errors to stdout but exits nonzero in this pinned build.
            sys.path.insert(0, str(ROOT/'tools/ref_tile'))
            import clock_entry_constraints as CE
            sys.path.insert(0, str(ROOT/'tools/closure_loop'))
            import ck_insertion as CK
            (p/'ce.tcl').write_text(CE.BODY.rsplit("\not_ce_apply\n",1)[0])
            (p/'ck.tcl').write_text(CK.ACTIVE_TCL)
            io = (ROOT/'physical/common_flow/io_ref_routed.sdc').read_text()
            (p/'io.tcl').write_text('proc ot_ir_arr {p {cn ""}} {' + io.split('proc ot_ir_arr {p {cn ""}} {')[2].split('\nif {[ot_ir_multi]')[0])
            pair = '  set ot_ce_glue {}' + CE.BODY.split('  set ot_ce_glue {}')[1].split('  # Preserve measured boundary spread:')[0]
            (p/'pairs.tcl').write_text(pair)
            (p/'run.tcl').write_text(script)
            cmd=['docker','run','--rm','-v',f'{FIXTURE}:/fixture:ro','-v',f'{SHARED.parent}:/shared:ro','-v',f'{p}:/run:ro','openroad/orfs:latest','/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/sta','-exit','/run/run.tcl']
            run=subprocess.run(cmd,text=True,capture_output=True)
            print(run.stdout, end='')
            return run

    def assert_native_pass(self, run):
        self.assertEqual(run.returncode, 0, run.stdout+run.stderr)
        self.assertNotIn('Error', run.stdout)
        self.assertTrue(run.stdout.rstrip().endswith('PASS'), run.stdout)

    def test_full_family_and_physical_master_segment(self):
        self.assert_native_pass(self.native('''
lassign [ot_cf_pins [get_clocks root]] pins owners
if {[lsort [lmap p $pins {get_full_name $p}]] ne {f0/CK f1/CK}} {error "wrong physical census"}
if {[get_full_name [dict get $owners f1/CK]] ne "bank"} {error "lost generated owner"}
assert_close [ot_cf_wire [get_pins f0/CK] [get_clocks root]] 3
assert_close [ot_cf_wire [get_pins f1/CK] [get_clocks bank]] 9
lassign [ot_cf_pins [get_clocks other]] foreign ignored
if {[lmap p $foreign {get_full_name $p}] ne {fo/CK}} {error "foreign root leaked"}
if {![catch {ot_cf_wire [get_pins f1/CK] [get_clocks root]}]} {error "wrong clock accepted"}
'''))

    def test_ce_native_and_routed_reference_agree(self):
        self.assert_native_pass(self.native('''
source /run/ce.tcl
source /run/ck.tcl
source /run/io.tcl
assert_close [ot_ce_clock_wire [get_pins f1/CK] [get_clocks root]] 9
assert_close [ot_ck_arr [get_pins f1/CK] [get_clocks root]] 9
assert_close [ot_ir_arr [get_pins f1/CK] root] 9
'''))

    def test_descendants_keep_cross_family_150_210_and_100_reserves(self):
        self.assert_native_pass(self.native(r'''
# Rebuild with entry root names, preserving actual bank ancestry.
delete_clock [all_clocks]
create_clock -name ot_entry_0 -period 100 [get_ports ck]
create_clock -name ot_entry_1 -period 100 [get_ports other]
create_generated_clock -name bank -source [get_ports ck] -master_clock ot_entry_0 -edges {3 4 11} [get_pins b1/Y]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
ot_cf_refresh
set ::ot_ce_ports {ck other}; set ::ot_ce_cts_roots {ck other}
foreach highname {{} ot_entry_1} {
 set highclocks {}; if {$highname ne ""} {set highclocks [get_clocks $highname]}
 source /run/pairs.tcl
 write_sdc /tmp/ot-family-pairs.sdc
 set fd [open /tmp/ot-family-pairs.sdc]; set text [read $fd];close $fd
 set setup [expr {[llength $highclocks] ? "210.0000" : "150.0000"}]
 foreach pair {{bank ot_entry_1} {ot_entry_1 bank}} {
  lassign $pair from to
  set found_setup 0;set found_hold 0
  foreach line [split $text \n] {
   if {[string first "get_clocks {$from}" $line] >= 0 && [string first "get_clocks {$to}" $line] >= 0} {
    if {[string first "-setup $setup" $line] >= 0} {set found_setup 1}
    if {[string first "-hold 100.0000" $line] >= 0} {set found_hold 1}
   }
  }
  if {!$found_setup || !$found_hold} {error "missing descendant reserve $from -> $to setup=$setup"}
 }
}
'''))

    def test_large_phase_removed_without_removing_physical_delay(self):
        self.assert_native_pass(self.native('assert_close [ot_cf_wire [get_pins f1/CK] [get_clocks bank]] 9', edges='7 8 15'))

    def test_source_compensation_is_not_silently_removed(self):
        self.assert_native_pass(self.native('assert_close [ot_cf_wire [get_pins f1/CK] [get_clocks bank]] 32', pre='set_clock_latency -source 23 [get_clocks root]'))

    def test_multiple_master_source_fails_closed(self):
        run=self.native(pre='create_clock -add -name rogue -period 100 [get_ports ck]')
        self.assertNotEqual(run.returncode,0,run.stdout)
        self.assertIn('generated source of bank has owners',run.stdout)

if __name__ == '__main__':
    unittest.main()
