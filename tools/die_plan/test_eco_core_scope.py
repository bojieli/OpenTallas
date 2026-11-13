"""Late ECO repairs exactly the core-owned endpoints used by eligibility."""
import json
import os
import subprocess
from pathlib import Path
import pytest
import eco_loop as E
from test_eco_loop import Fake, kit, rec, base_rec


def mixed(k, core=8, inputs=2105, outputs=255):
    b = base_rec(k, rec(5, -500))
    d = b.parent / 'ff'
    d.mkdir(exist_ok=True)
    census = dict(port=inputs, other=core, reg=core, oport=outputs, core_n=core,
                  core_wns=-8 if core else 0, nonport_n=core+outputs,
                  nonport_wns=-42 if core+outputs else 0, err=0, trunc=0)
    (d / 'corner.json').write_text(json.dumps(dict(std_min_start=census)))
    return b


def run_scoped(tmp_path, monkeypatch, env=None, config=None):
    monkeypatch.delenv('OT_HOLD_REPAIR_SCOPE', raising=False)
    if env is not None: monkeypatch.setenv('OT_HOLD_REPAIR_SCOPE', env)
    k = kit(tmp_path, mm=False)
    if config is not None:
        with (k/'config.mk').open('a') as f: f.write('export OT_HOLD_REPAIR_SCOPE = '+config+'\n')
    b = mixed(k)
    fake = Fake([rec(5, 1)])
    result = E.run_loop(k, b, run=fake, mem=8, cpus=1, strict_one_pass=True)
    runs = [(cmd, env) for cmd, env in fake.calls if cmd[0] == 'bash' and cmd[1].endswith('prd_run.sh')]
    assert result['verdict'] == 'PASS' and len(runs) == 1 and len(result['iterations']) == 1
    return result, runs[0][1]


def test_default_matches_core_census_and_does_not_leak(tmp_path, monkeypatch):
    result, env = run_scoped(tmp_path, monkeypatch)
    assert env['OT_HOLD_REPAIR_SCOPE'] == result['hold_repair_scope'] == 'reg2reg'
    assert result['base_metrics']['ff_core_n'] == 8
    assert result['base_metrics']['ff_core'] == -8
    assert result['base_metrics']['hold_score_scope'] == 'core'
    assert result['physical_dispatch_budget']['dispatched'] == 1
    assert 'OT_HOLD_REPAIR_SCOPE' not in os.environ and E.hold_scope() == ''


@pytest.mark.parametrize('value', ['nonport', 'all', ''])
def test_explicit_environment_scope_retains_legacy_meaning(tmp_path, monkeypatch, value):
    result, env = run_scoped(tmp_path, monkeypatch, env=value)
    assert env['OT_HOLD_REPAIR_SCOPE'] == value and result['hold_repair_scope'] == value
    if value == 'nonport':
        assert result['base_metrics']['ff_np_n'] == 263 and 'ff_core_n' not in result['base_metrics']
    else:
        assert 'ff_np_n' not in result['base_metrics']


def test_explicit_kit_scope_and_environment_precedence(tmp_path, monkeypatch):
    result, env = run_scoped(tmp_path/'a', monkeypatch, config='nonport')
    assert env['OT_HOLD_REPAIR_SCOPE'] == result['hold_repair_scope'] == 'nonport'
    result, env = run_scoped(tmp_path/'b', monkeypatch, env='all', config='nonport')
    assert env['OT_HOLD_REPAIR_SCOPE'] == result['hold_repair_scope'] == 'all'


@pytest.mark.parametrize('inputs,outputs', [(2105, 0), (2105, 255), (0, 255)])
def test_parent_only_hold_never_launches_eco(tmp_path, monkeypatch, inputs, outputs):
    monkeypatch.delenv('OT_HOLD_REPAIR_SCOPE', raising=False)
    k = kit(tmp_path, mm=False)
    b = mixed(k, core=0, inputs=inputs, outputs=outputs)
    fake = Fake([])
    result = E.run_loop(k, b, run=fake, mem=8, cpus=1)
    assert result['verdict'] == 'NOT_ELIGIBLE' and not fake.calls
    assert not E.eligible(E.load(b), b)[0]


def test_declared_route_hold_path_does_not_get_late_default(tmp_path, monkeypatch):
    monkeypatch.delenv('OT_HOLD_REPAIR_SCOPE', raising=False)
    seen = []
    monkeypatch.setattr(E, '_run_loop', lambda **kw: seen.append(E.hold_scope()) or {'verdict': 'fixture'})
    E.run_loop(tmp_path, tmp_path/'signoff.json', route_hold_form=True)
    assert seen == [''] and E.hold_scope() == ''


def _tcl_scope_script(tmp_path, scope):
    # Execute the actual shared scope procedure, with minimal STA collection mocks.
    src = (E.HERE.parent/'orfs_hold_mm.tcl').read_text()
    start = src.index('proc ot_hold_scope_read ')
    proc = src.index('proc ot_hold_repair_scope ', start)
    end = src.index('\n}\n', proc)+3
    script = src[start:end] + r'''
namespace eval sta { proc cmd_mode_name {} { return tt } }
set ::ot_mm_synced 1
set ::ot_mm_stage 4_cts.sdc
set ::excluded_in {}
set ::excluded_out {}
proc set_mode {m} {}
proc all_clocks {} { return core_clk }
proc get_property {obj key} { return clk }
proc get_full_name {obj} { return $obj }
proc all_inputs {} { set p {clk}; for {set i 0} {$i < 2105} {incr i} { lappend p in$i }; return $p }
proc all_outputs {} { set p {}; for {set i 0} {$i < 255} {incr i} { lappend p out$i }; return $p }
proc set_false_path {args} {
 if {[lsearch $args -from] >= 0} { set ::excluded_in [lindex $args end] }
 if {[lsearch $args -to] >= 0} { set ::excluded_out [lindex $args end] }
}
proc unset_path_exceptions {args} {
 if {[lsearch $args -from] >= 0} { set ::excluded_in {} }
 if {[lsearch $args -to] >= 0} { set ::excluded_out {} }
}
proc write_sdc {args} { set f [open [lindex $args end] w]; puts $f original; close $f }
proc read_sdc {args} {}
proc ot_hold_stats {} { return [expr {8 + (2105-[llength $::excluded_in]) + (255-[llength $::excluded_out])}] }
set ::env(OT_HOLD_REPAIR_SCOPE) SELECTED_SCOPE
set ::env(RESULTS_DIR) {WORKDIR}
ot_hold_repair_scope { puts "SELECTED [ot_hold_stats]" }
puts "RESTORED [ot_hold_stats]"
'''
    script = script.replace('SELECTED_SCOPE', scope).replace('WORKDIR', str(tmp_path))
    return script


@pytest.mark.parametrize('scope,count', [('reg2reg', 8), ('nonport', 263), ('all', 2368)])
def test_actual_tcl_scope_keeps_exact_core8_and_preserves_overrides(tmp_path, scope, count):
    result = subprocess.run(['tclsh'], input=_tcl_scope_script(tmp_path, scope), text=True, capture_output=True)
    assert result.returncode == 0 and 'SELECTED '+str(count)+'\n' in result.stdout, result.stdout+result.stderr
    assert 'RESTORED 2368' in result.stdout


@pytest.mark.parametrize('synced,stage', [(None, '4_cts.sdc'), (0, '4_cts.sdc'), (1, '5_1_grt.sdc'), (1, '4_cts.sdc')])
def test_actual_postroute_wrapper_never_delegates_unscoped_mm(tmp_path, synced, stage):
    src = (E.PRD/'prd_hook.tcl').read_text()
    start = src.index('proc ot_prd_hold_scope ')
    end = src.index('\n}\n', start)+3
    wrapper = src[start:end]
    check = src.index('proc ot_prd_hold_scope_assert ')
    wrapper += '\n' + src[check:src.index('\n}\n', check)+3]
    script = 'set ::ot_mm_active 1\n' + _tcl_scope_script(tmp_path, 'reg2reg')
    if synced is None:
        script = script.replace('set ::ot_mm_synced 1', 'unset -nocomplain ::ot_mm_synced')
    else:
        script = script.replace('set ::ot_mm_synced 1', 'set ::ot_mm_synced '+str(synced))
    script = script.replace('set ::ot_mm_stage 4_cts.sdc', 'set ::ot_mm_stage '+stage)
    old = 'ot_hold_repair_scope { puts "SELECTED [ot_hold_stats]" }'
    call = wrapper+'\nset failed [catch {ot_prd_hold_scope {puts "SELECTED [ot_hold_stats]"}} why]\nputs "FAILED $failed $why"'
    call += '\nset check [catch {ot_prd_hold_scope_assert} why]\nputs "VERIFY_FAIL $check $why"'
    assert old in script
    script = script.replace(old, call)
    result = subprocess.run(['tclsh'], input=script, text=True, capture_output=True)
    assert result.returncode == 0, result.stdout+result.stderr
    if synced == 1 and stage == '4_cts.sdc':
        assert 'SELECTED 8' in result.stdout and 'FAILED 0' in result.stdout
        assert 'OT_HOLD_SCOPE repair_ff=' in result.stdout
        assert 'OT_PRD_HOLD_SCOPE_VERIFIED scope=reg2reg' in result.stdout and 'VERIFY_FAIL 0' in result.stdout
    else:
        assert 'SELECTED ' not in result.stdout and 'FAILED 1' in result.stdout
        assert 'refusing unscoped late repair' in result.stdout
        assert 'OT_PRD_HOLD_SCOPE_VERIFIED' not in result.stdout and 'VERIFY_FAIL 1' in result.stdout
    assert 'RESTORED 2368' in result.stdout


def test_missing_actual_openroad_scope_fails_before_body(tmp_path):
    src = (E.PRD/'prd_hook.tcl').read_text()
    start = src.index('proc ot_prd_hold_scope ')
    wrapper = src[start:src.index('\n}\n', start)+3]
    script = wrapper + '\nset ::ot_prd_expected_hold_scope reg2reg\nunset -nocomplain ::env(OT_HOLD_REPAIR_SCOPE)\n'
    script += 'set failed [catch {ot_prd_hold_scope {puts UNSCOPED_BODY}} why]\nputs "FAILED $failed $why"\n'
    result = subprocess.run(['tclsh'], input=script, text=True, capture_output=True)
    assert 'UNSCOPED_BODY' not in result.stdout and 'FAILED 1' in result.stdout
    assert 'actual OpenROAD environment' in result.stdout


def test_no_runtime_scope_receipt_cannot_be_accepted(tmp_path, monkeypatch):
    monkeypatch.delenv('OT_HOLD_REPAIR_SCOPE', raising=False)
    k = kit(tmp_path, mm=False)
    b = mixed(k)
    class MissingTrace(Fake):
        def __call__(self, cmd, **kw):
            rc = super().__call__(cmd, **kw)
            if cmd[0] == 'bash' and cmd[1].endswith('prd_run.sh'):
                (Path(cmd[2])/'run_prd.log').write_text('hold stage returned without scope body\n')
            return rc
    result = E.run_loop(k, b, run=MissingTrace([rec(5, 1)]), mem=8, cpus=1, strict_one_pass=True)
    assert result['verdict'] == 'ERROR' and 'no runtime completion receipt' in result['reason']


def test_tt_only_pass_needs_no_hold_completion_marker(tmp_path, monkeypatch):
    monkeypatch.delenv('OT_HOLD_REPAIR_SCOPE', raising=False)
    monkeypatch.setattr(E, 'passes', lambda *args: ['t0'])
    k = kit(tmp_path, mm=False)
    b = base_rec(k, rec(-5, 1))
    class TTOnly(Fake):
        def __call__(self, cmd, **kw):
            rc = super().__call__(cmd, **kw)
            if cmd[0] == 'bash' and cmd[1].endswith('prd_run.sh'):
                (Path(cmd[2])/'run_prd.log').write_text('hold: skipped OT_PRD_NO_HOLD=1\n')
            return rc
    result = E.run_loop(k, b, run=TTOnly([rec(5, 1)]), mem=8, cpus=1, strict_one_pass=True)
    assert result['verdict'] == 'PASS' and result['physical_dispatch_budget']['dispatched'] == 1


def test_scope_is_pinned_in_config_and_actual_hook(tmp_path, monkeypatch):
    monkeypatch.setenv('OT_HOLD_REPAIR_SCOPE', 'reg2reg')
    (tmp_path/'config.mk').write_text('export OT_HOLD_REPAIR_SCOPE = all\n')
    (tmp_path/'prd_hook.tcl').write_text((E.PRD/'prd_hook.tcl').read_text())
    assert E.pin_late_hold_scope(tmp_path) == 'reg2reg'
    assert (tmp_path/'config.mk').read_text().endswith('override export OT_HOLD_REPAIR_SCOPE = reg2reg\n')
    assert (tmp_path/'prd_hook.tcl').read_text().startswith('set ::ot_prd_expected_hold_scope reg2reg\n')


def test_postcondition_refuses_callback_that_never_ran(tmp_path):
    src = (E.PRD/'prd_hook.tcl').read_text()
    start = src.index('proc ot_prd_hold_scope_assert ')
    proc = src[start:src.index('\n}\n', start)+3]
    script = proc+'\nset ::ot_prd_expected_hold_scope reg2reg\n'
    script += 'set failed [catch {ot_prd_hold_scope_assert} why]\nputs "FAILED $failed $why"\n'
    result = subprocess.run(['tclsh'], input=script, text=True, capture_output=True)
    assert 'FAILED 1' in result.stdout and 'missing runtime ot_prd_scope_entered' in result.stdout
    assert 'OT_PRD_HOLD_SCOPE_VERIFIED' not in result.stdout
    control = script+'\nset ::env(OT_PRD_NO_HOLD) 1\nset okay [catch {ot_prd_hold_scope_assert}]\nputs "NO_HOLD $okay"\n'
    result = subprocess.run(['tclsh'], input=control, text=True, capture_output=True)
    assert 'NO_HOLD 0' in result.stdout


def test_scope_pinning_detaches_shared_inodes(tmp_path, monkeypatch):
    monkeypatch.setenv("OT_HOLD_REPAIR_SCOPE", "reg2reg")
    donor, pd = tmp_path/"donor", tmp_path/"pass"
    donor.mkdir(); pd.mkdir()
    originals = {"config.mk": "export DESIGN_NAME = x\n", "prd_hook.tcl": (E.PRD/"prd_hook.tcl").read_text()}
    for name, text in originals.items():
        (donor/name).write_text(text)
        os.link(donor/name, pd/name)
    E.pin_late_hold_scope(pd)
    for name, text in originals.items():
        assert (donor/name).read_text() == text
        assert (donor/name).stat().st_ino != (pd/name).stat().st_ino


def test_old_custom_hook_refused_before_any_scope_write(tmp_path, monkeypatch):
    monkeypatch.setenv("OT_HOLD_REPAIR_SCOPE", "reg2reg")
    (tmp_path/"config.mk").write_text("original config\n")
    (tmp_path/"prd_hook.tcl").write_text("# old unobserved custom hook\n")
    with pytest.raises(ValueError, match="lacks the runtime scope postcondition"):
        E.pin_late_hold_scope(tmp_path)
    assert (tmp_path/"config.mk").read_text() == "original config\n"
