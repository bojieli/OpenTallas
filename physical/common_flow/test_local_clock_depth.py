from pathlib import Path
import subprocess


def test_sparse_clock_depth_is_opt_in_and_compact():
    source = Path(__file__).with_name('local_clock_depth.tcl')
    script = 'source {' + str(source) + '}\n' + r'''
proc assert {yes msg} {if {![uplevel 1 [list expr $yes]]} {puts stderr $msg;exit 1}}
assert {[ot_local_depth::pad_short_taps {}] == 0} "source/default must not change a database"
set ::env(OT_DTAP_PAD_SPARSE) 1
assert {[catch {ot_local_depth::pad_short_taps {}}]} "requires explicit planned runtime"
namespace eval ot_dtsh {variable active 1;variable rows {0 {{0 1 100 1 R0}} 2 {{0 1 100 1 R0}}}}
set ::env(OT_DTAP_PAD_DEPTH) 4
assert {[catch {ot_local_depth::pad_short_taps {}}]} "reject unbounded local depth"
unset ::env(OT_DTAP_PAD_DEPTH)
set ::env(OT_DTAP_PAD_RADIUS_UM) 11
assert {[catch {ot_local_depth::pad_short_taps {}}]} "reject noncompact island"
unset ::env(OT_DTAP_PAD_RADIUS_UM)
proc ot_dtsh::check_site {x y orient} {if {$x != 12 || $y != 2 || $orient ne "R0"} {error occupied}}
assert {[ot_local_depth::site_near 10 0 4] eq {12 2 R0}} "uses only a legal nearby free footprint"
assert {[catch {ot_local_depth::site_near 10 0 3}]} "fails closed when compact free site is unavailable"
assert {[catch {ot_local_depth::sinks ignored 41}]} "clock graph recursion bounded"
puts "PASS sparse clock guards"
'''
    result = subprocess.run(['tclsh'], input=script, text=True, capture_output=True)
    assert result.returncode == 0 and 'PASS sparse clock guards' in result.stdout, (result.stdout, result.stderr)
