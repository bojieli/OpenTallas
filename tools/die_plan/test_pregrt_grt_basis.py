"""Closed-GRT reuse of native TC/BC hold repair, with final signal RC and internal scope."""
import importlib.util
import os
from pathlib import Path
import re
import shutil
import subprocess
import pytest

HERE = Path(__file__).resolve().parent
if (HERE / 'pregrt_ff_hold.after.py').exists():
    spec = importlib.util.spec_from_file_location('PG', HERE / 'pregrt_ff_hold.after.py')
    PG = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(PG)
else:
    import pregrt_ff_hold as PG


def run_tcl(tmp_path, text):
    if not shutil.which('tclsh'):
        pytest.skip('tclsh unavailable')
    script = tmp_path / 'check.tcl'
    script.write_text(text)
    return subprocess.run(['tclsh', str(script)], capture_output=True, text=True)


def rendered():
    return PG.tcl_text((HERE / 'hold_gate.tcl').read_text(), rc_basis='global_routing')


def test_default_placement_uses_original_exact_context_and_tail():
    head = (HERE / 'hold_gate.tcl').read_text().split(PG.MARK)[0]
    old = head.replace(PG.READ, PG.READ2) + PG.tail_text(-1)
    assert PG.tcl_text((HERE / 'hold_gate.tcl').read_text()) == old
    with pytest.raises(ValueError):
        PG.tcl_text((HERE / 'hold_gate.tcl').read_text(), rc_basis='guessed')


def test_grt_requires_real_setup_scene(tmp_path):
    result = run_tcl(tmp_path, 'set env(TLIBS) {}\n' + PG.GRT_CONTEXT)
    assert result.returncode != 0
    assert 'requires real TC setup and BC hold libraries' in result.stderr


def test_effective_signal_rc_and_exact_scope_restore(tmp_path):
    (tmp_path / 'config.mk').write_text('export OT_RC_SIGNAL = 1\nexport OT_RC_SIGNAL_SCALE = 1.13\n')
    (tmp_path / 'constraint.sdc').write_text('# OT_CORE_TAP_CORNER_FILE core_taps_ff.sdc\n')
    (tmp_path / 'core_taps_ff.sdc').write_text('# actual FF tap overlay\n')
    (tmp_path / 'rc_signal_adjust.tcl').write_text('proc ot_rc_signal_table {} {puts "RC_SIGNAL $::env(OT_RC_SIGNAL_SCALE)"}\n')
    prelude = r'''
set env(TLIBS) TC_libs
set env(SDC) [file join [file dirname [info script]] constraint.sdc]
set env(OT_RC_SIGNAL_SCALE) wrong_caller_value
proc estimate_parasitics {args} {puts "ESTIMATE $args"}
proc read_sdc {args} {puts "READ $args"}
proc write_sdc {args} {set f [open [lindex $args end] w];puts $f {# exact existing FF exceptions};close $f;puts SAVE}
proc all_inputs {args} {return in0}
proc all_outputs {} {return out0}
proc set_false_path {args} {puts "MASK $args"}
proc unset_path_exceptions {args} {puts "UNMASK $args"}
proc set_mode {mode} {puts "MODE $mode"}
'''
    result = run_tcl(tmp_path, prelude + PG.GRT_CONTEXT + '\npg_refresh_rc\npg_grt_ff_taps\npg_scope_begin\npg_scope_end\npg_refresh_rc\n')
    assert result.returncode == 0, result.stderr
    lines = result.stdout.splitlines()
    assert lines.count('ESTIMATE -global_routing') == 2
    assert lines.count('RC_SIGNAL 1.13') == 2
    assert lines.index('SAVE') < lines.index('MASK -hold -from in0')
    restore = next(i for i, l in enumerate(lines) if l.startswith('READ -mode ff') and l.endswith('pregrt_ff_hold_scope.sdc'))
    assert lines.index('UNMASK -hold -to out0') < restore < len(lines)-2
    assert any(l.startswith('READ -mode ff') and l.endswith('core_taps_ff.sdc') for l in lines)


def test_illegal_placement_is_rejected_only_for_grt(tmp_path):
    prelude = r'''
proc detailed_placement {args} {}
proc check_placement {args} {
  set i [lsearch -exact $args -report_file_name]
  if {$i >= 0} {set f [open [lindex $args [expr {$i+1}]] w];puts $f overlap;close $f}
  error {overlap remains}
}
'''
    default = PG.tcl_text((HERE / 'hold_gate.tcl').read_text())
    for text, expected in ((default, 0), (rendered(), 1)):
        i = text.index('  set pg_legal negotiation;')
        end = text.index('  pg_refresh_rc' if expected else '  estimate_parasitics -placement', i)
        result = run_tcl(tmp_path, prelude + 'set status [catch {\n' + text[i:end] + '\n} message]\nputs "STATUS $status $message"\n')
        assert result.returncode == 0, result.stderr
        assert f'STATUS {expected}' in result.stdout
        if expected:
            assert 'requires legal placement' in result.stdout


def test_grt_replays_constraints_and_restores_scope_before_output(tmp_path):
    t = rendered()
    assert 'define_scene TC -mode tt' in t and 'define_scene BC -mode ff' in t
    assert 'ot_mm_active' not in t
    assert 'estimate_parasitics -placement' not in t
    assert t.index('ot_grt_pg_replay_begin $pg_grt_dir') < t.index('global_route -start_incremental') < t.index('pg_repair_hold $pg_tag')
    assert t.index('global_route -end_incremental\n  ot_grt_pg_replay_end') < t.index('  pg_refresh_rc', t.index('set pg_legal negotiation'))
    assert 'global_route -end_incremental -allow_congestion' not in t
    assert t.index('catch {pg_scope_end}') < t.index('pg_classes after $pg_open') < t.index('write_guides $pg_guide') < t.index('write_db $::env(ODB).pg_tmp')
    assert 'internal FF hold remains negative' in t
    check = tmp_path / 'rendered.tcl'
    check.write_text(t)
    result = run_tcl(tmp_path, f'set f [open {{{check}}}];set t [read $f];close $f\nputs [info complete $t]\n')
    assert result.stdout.strip() == '1'
