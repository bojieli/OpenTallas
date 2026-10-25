import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import partition_ir as ir

FIXTURE = Path(__file__).parent / 'fixtures' / 'partition_ir'


def stage(tmp_path):
    scripts = tmp_path / 'scripts'
    shutil.copytree(FIXTURE, scripts)
    assert ir.patch(scripts)
    (scripts / 'load.tcl').write_text('')
    return scripts


MOCK = r'''
namespace eval utl {proc set_metrics_stage {args} {}}
namespace eval ord {proc openroad_gui_compiled {} {return 0}}
proc erase_non_stage_variables {args} {}
proc source_step_tcl {args} {}
proc load_design {odb sdc} {puts "LOAD $odb $sdc"}
proc set_propagated_clock {args} {}
proc all_clocks {} {return {clk vclk}}
proc global_connect {} {}
proc deleteRoutingObstructions {} {}
proc write_def {args} {}
proc write_verilog {args} {}
proc find_physical_only_masters {} {return {}}
proc define_process_corner {args} {}
proc extract_parasitics {args} {puts RCX}
proc write_spef {path} {set fp [open $path w];close $fp;puts SPEF}
proc read_spef {path} {puts READ_SPEF}
proc set_pdnsim_net_voltage {args} {puts "VOLTAGE $args"}
proc analyze_power_grid {args} {
  puts "IR $args"
  if {[info exists ::env(TEST_IR_FAIL)]} {error {simulated IR failure}}
}
proc report_cell_usage {} {}
proc report_metrics {args} {puts METRICS}
proc env_var_exists_and_non_empty {key} {
  expr {[info exists ::env($key)] && $::env($key) ne ""}
}
proc orfs_write_db {path} {set fp [open $path w];close $fp;puts DB}
proc orfs_write_sdc {path} {set fp [open $path w];close $fp;puts SDC}
'''


def run_tcl(tmp_path, scripts, *, defer=False, sidecar=False, fail=False, hook=False):
    results = tmp_path / 'results'
    results.mkdir(exist_ok=True)
    (scripts / 'deleteRoutingObstructions.tcl').write_text('')
    (tmp_path / 'top.totCap').write_text('')
    command = tmp_path / 'execute.tcl'
    command.write_text(MOCK + '\nsource $::env(SCRIPTS_DIR)/final_report.tcl\n')
    env = dict(os.environ, SCRIPTS_DIR=str(scripts), RESULTS_DIR=str(results),
               REPORTS_DIR=str(tmp_path / 'reports'), DESIGN_NAME='top',
               RCX_RULES='asap7.rules', SKIP_DETAILED_ROUTE='0',
               PWR_NETS_VOLTAGES='VDD 0.7', GND_NETS_VOLTAGES='VSS 0',
               OT_DEFER_PARTITION_IR=str(int(defer)),
               OT_PARTITION_IR_SIDECAR=str(int(sidecar)),
               OT_PARTITION_IR_STATUS=str(tmp_path / 'sidecar.status'))
    if fail:
        env['TEST_IR_FAIL'] = '1'
    if hook:
        env['PRE_FINAL_REPORT_TCL'] = '/custom/unknown_pdnsim_state.tcl'
    return subprocess.run(['tclsh', str(command)], cwd=tmp_path, env=env,
                          text=True, capture_output=True)


def test_actual_image_patch_keeps_original_ir_and_is_idempotent(tmp_path):
    scripts = stage(tmp_path)
    old = (FIXTURE / 'final_outputs.tcl').read_text()
    expected = old[old.index(ir.ANCHOR):old.index(ir.END)]
    assert (scripts / 'partition_ir_analysis.tcl').read_text() == expected
    before = {p.name: p.read_bytes() for p in scripts.iterdir()}
    assert not ir.patch(scripts)
    assert before == {p.name: p.read_bytes() for p in scripts.iterdir()}


def test_default_retains_original_ir_and_native_checkpoint_order(tmp_path):
    run = run_tcl(tmp_path, stage(tmp_path))
    assert run.returncode == 0, run.stderr
    assert run.stdout.index('\nDB\n') < run.stdout.index('IR -net VDD')
    assert 'NOT_RUN' not in run.stdout


def test_defer_returns_final_artifacts_and_explicit_not_run(tmp_path):
    scripts = stage(tmp_path)
    run = run_tcl(tmp_path, scripts, defer=True)
    assert run.returncode == 0, run.stderr
    assert 'IR -net ' not in run.stdout
    assert run.stdout.index('\nDB\n') < run.stdout.index('READ_SPEF')
    assert 'OT_PARTITION_IR NOT_RUN' in run.stdout and 'METRICS' in run.stdout
    results = tmp_path / 'results'
    assert all((results / f'6_final.{suffix}').exists() for suffix in ('odb', 'sdc', 'spef'))
    markers = list(results.glob('partition_ir_deferred_*.status'))
    assert len(markers) == 1 and markers[0].read_text().startswith('NOT_RUN ')


def test_separate_sidecar_reuses_artifacts_and_original_ir(tmp_path):
    scripts = stage(tmp_path)
    assert run_tcl(tmp_path, scripts, defer=True).returncode == 0
    run = run_tcl(tmp_path, scripts, sidecar=True)
    assert run.returncode == 0, run.stderr
    assert 'LOAD 6_final.odb 6_final.sdc' in run.stdout
    assert 'READ_SPEF' in run.stdout and 'IR -net VDD' in run.stdout and 'IR -net VSS' in run.stdout
    assert 'RCX\n' not in run.stdout and '\nDB\n' not in run.stdout
    assert (tmp_path / 'sidecar.status').read_text().startswith('COMPLETED analysis_only')


def test_sidecar_failure_is_recorded_and_propagated(tmp_path):
    scripts = stage(tmp_path)
    assert run_tcl(tmp_path, scripts, defer=True).returncode == 0
    run = run_tcl(tmp_path, scripts, sidecar=True, fail=True)
    assert run.returncode != 0
    assert (tmp_path / 'sidecar.status').read_text().startswith('FAIL simulated IR failure')


def test_sidecar_missing_spef_cannot_complete(tmp_path):
    scripts = stage(tmp_path)
    run = run_tcl(tmp_path, scripts, sidecar=True)
    assert run.returncode != 0 and 'requires final RCX SPEF' in run.stderr


def test_arbitrary_solver_hook_cannot_be_silently_lost(tmp_path):
    run = run_tcl(tmp_path, stage(tmp_path), defer=True, hook=True)
    assert run.returncode != 0 and 'cannot capture arbitrary PRE_FINAL_REPORT_TCL' in run.stderr


def test_unknown_image_anchor_fails_before_any_mutation(tmp_path):
    scripts = tmp_path / 'scripts'
    shutil.copytree(FIXTURE, scripts)
    f = scripts / 'final_outputs.tcl'
    f.write_text(f.read_text().replace(ir.ANCHOR, '  # unknown IR layout\n'))
    before = {p.name: p.read_bytes() for p in scripts.iterdir()}
    with pytest.raises(ValueError, match='boundaries'):
        ir.patch(scripts)
    assert before == {p.name: p.read_bytes() for p in scripts.iterdir()}
