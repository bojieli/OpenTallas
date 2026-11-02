"""Clock sizing protection must restore hold-repair freedom, including errors."""
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HOOK = ROOT / "physical/die_plan/qwen_kvsys/cores/harden/eco/eco_route.tcl"


def test_clock_master_scope_and_error_cleanup():
    text = HOOK.read_text()
    helper = text[text.index("proc kvc_preserve_clock_masters"):text.index("proc kvc_drv")]
    mock = r"""
set dt(sink) 0
set dt(driver) 1
set dt(other) 0
proc ot_clk_dbnets {} { return {net} }
proc net {method} { if {$method eq "getITerms"} { return {pin1 pin2 pin3} }; error $method }
proc pin1 {method} { return sink }
proc pin2 {method} { return driver }
proc pin3 {method} { return sink }
foreach obj {sink driver other} {
    proc $obj {method args} [string map [list @OBJ@ $obj] {
        switch $method {
            getName { return @OBJ@ }
            isDoNotTouch { return $::dt(@OBJ@) }
            setDoNotTouch { set ::dt(@OBJ@) [lindex $args 0] }
            default { error $method }
        }
    }]
}
proc require {value message} { if {![uplevel 1 [list expr $value]]} { error $message } }
set caller 0
kvc_preserve_clock_masters {
    require {$dt(sink) == 1 && $dt(driver) == 1 && $dt(other) == 0} "wrong sizing protection"
    set caller 1
}
require {$caller == 1} "lost caller scope"
require {$dt(sink) == 0 && $dt(driver) == 1} "hold state not restored"
set rc [catch {kvc_preserve_clock_masters {error real_repair_failure}} message]
require {$rc == 1 && $message eq "real_repair_failure"} "repair error swallowed"
require {$dt(sink) == 0 && $dt(driver) == 1} "error cleanup broke protection"
puts PASS
"""
    result = subprocess.run(["tclsh"], input=helper + mock, text=True, capture_output=True)
    assert result.returncode == 0 and "PASS" in result.stdout and not result.stderr, result
