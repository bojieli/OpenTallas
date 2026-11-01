import importlib.util
from pathlib import Path
import subprocess

SPEC = importlib.util.spec_from_file_location("mm_power", Path(__file__).with_name("orfs_hold_mm.py"))
MM = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MM)

FIXTURE = 'proc report_metrics {stage when} {\n  global filename\n  incr ::timing\n  report_puts "\\n=========================================================================="\n  report_puts "$when report_power"\n  report_puts "--------------------------------------------------------------------------"\n  if { [env_var_exists_and_non_empty CORNERS] } {\n    foreach corner $::env(CORNERS) {\n      report_puts "Corner: $corner"\n      report_power -corner $corner >> $filename\n      report_power_metric -corner $corner\n    }\n    unset corner\n  } else {\n    report_power >> $filename\n    report_power_metric\n  }\n\n  # TODO these only work to stdout, whereas we want to append to the $filename\n  incr ::area\n}\n'


def test_intermediate_omits_power_final_and_dedicated_keep_it(tmp_path):
    p = tmp_path / "report_metrics.tcl"
    p.write_text(FIXTURE)
    assert MM.patch_intermediate_power(tmp_path) == "patched"
    assert MM.patch_intermediate_power(tmp_path) == "already patched"
    script = """
set timing 0; set area 0; set power 0; set power_metric 0
set filename /dev/null
set ::env(CORNERS) {tc bc}
proc report_puts {args} {}
proc env_var_exists_and_non_empty {args} {return 1}
proc report_power {args} {incr ::power}
proc report_power_metric {args} {incr ::power_metric}
source SOURCE
report_metrics 3 intermediate
if {$timing != 1 || $area != 1 || $power != 0 || $power_metric != 0} {error intermediate}
report_metrics 6 finish
if {$timing != 2 || $area != 2 || $power != 2 || $power_metric != 2} {error final}
report_metrics custom dedicated
if {$timing != 3 || $area != 3 || $power != 4 || $power_metric != 4} {error custom}
report_power
if {$power != 5} {error dedicated}
puts PASS
""".replace("SOURCE", "{" + str(p) + "}")
    result = subprocess.run(["tclsh"], input=script, text=True, capture_output=True, check=True)
    assert "PASS" in result.stdout
    assert "OT_INTERMEDIATE_POWER_SKIPPED stage 3" in result.stdout
    assert result.stderr == ""
