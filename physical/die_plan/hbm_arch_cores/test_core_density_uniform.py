from pathlib import Path
import subprocess
s=Path(__file__).with_name('core_density_taps.tcl').read_text().split('uplevel #0 {')[0]
t=s+'''
set dt_msplit_on 0
proc assert {yes msg} {if {![uplevel 1 [list expr $yes]]} {puts stderr $msg; exit 1}}
set a {{0 0 a} {1 0 b}}
set b {{3 0 c} {4 0 d}}
set c {{100 0 e} {101 0 f}}
set out [dt_uniform_merge [list $a $b $c] 3 4 10]
assert {[llength $out] == 2} "near groups merge"
assert {[llength [lindex $out 0]]+[llength [lindex $out 1]] == 6} "sinks retained"
set out [dt_uniform_merge [list $a $b] 3 3 10]
assert {[llength $out] == 2} "sink cap"
set out [dt_uniform_merge [list $a $b] 3 4 2]
assert {[llength $out] == 2} "geometry cap"
set dt_msplit_on 1
proc dt_straddle {pts} {return {0 2}}
set out [dt_uniform_merge [list $a $b] 3 4 10]
assert {[llength $out] == 2} "macro straddle rejected"
set dt_msplit_on 0
assert {[dt_uniform_merge {} 3 4 10] eq {}} "empty input"
assert {[catch {dt_uniform_merge [list $a] 5 4 10}]} "bad configuration"
puts "PASS 6 uniform-group cases"
'''
def test_uniform_group_geometry_and_preservation():
    r = subprocess.run(['tclsh'], input=t, text=True, capture_output=True)
    assert r.returncode == 0 and 'PASS 6' in r.stdout, (r.stdout, r.stderr)
