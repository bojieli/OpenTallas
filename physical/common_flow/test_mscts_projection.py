from pathlib import Path
import subprocess


def test_discrete_window_projection_actual_prog_case_and_negative_controls():
    source = Path(__file__).with_name('mscts_projection.tcl')
    code = 'source {' + str(source) + '}\n' + r'''
proc assert {yes msg} {if {![uplevel 1 [list expr $yes]]} {puts stderr $msg;exit 1}}
set arrivals {P0 516.2 R0E 526.5 R0W 515.8 R1E 521.7 R1W 520.2 R2E 511.4 R2W 519.8 R3E 524 R3W 525.5 S0 519.2 S1 508.1 S2 528.6 S3 524.2}
set steps {};dict for {k a} $arrivals {dict set steps $k 23.0}
set p [ot_ms_projection::select $arrivals $steps 20]
assert {[dict get $p feasible] == 1} "actual finishing solution exists"
assert {[dict get $p counts] eq {S1 1}} "actual solution is one S1 pad, no extra edits"
assert {abs([dict get $p span]-19.7) < 1e-8} "unchanged20pswindow"
assert {abs([dict get $p added_latency_ps]-2.5) < 1e-8} "physical added latency reported"
# A zero-edit mutant cannot cure the original measured20.5ps residual.
set vals [lsort -real [dict values $arrivals]]
assert {[lindex $vals end]-[lindex $vals 0] > 20} "zero-edit control must fail"
set p [ot_ms_projection::select {a 500 b 519} {a 23 b 23} 20]
assert {[dict get $p counts] eq {}} "already passing window gets no edits"
assert {[catch {ot_ms_projection::select {a 1} {b 23} 20}]} "membership mismatch"
assert {[catch {ot_ms_projection::select {a 1} {a -1} 20}]} "uncalibrated step"
set p [ot_ms_projection::select {a 0 b 100} {a 23 b 23} 20]
assert {![dict get $p feasible]} "coarse tree not retargeted by finishing selector"
set p [ot_ms_projection::select {a 0 b 21} {a 40 b 40} 20 0]
assert {![dict get $p feasible]} "rise bound never relaxed"
puts "PASS projection plus negative controls"
'''
    result = subprocess.run(['tclsh'], input=code, text=True, capture_output=True)
    assert result.returncode == 0 and 'PASS projection plus negative controls' in result.stdout, (result.stdout, result.stderr)
