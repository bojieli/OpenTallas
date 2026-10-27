"""Execute the actual generated PG window gate tail, with native-tool controls."""
from pathlib import Path
import subprocess
import sys
import pytest

sys.path.insert(0, str(Path(__file__).parent))
import die_trial as D
import infra_pg
import phy_ir


@pytest.fixture(params=['infra', 'phy'])
def generated_tail(request, tmp_path):
    plan = Path(__file__).parent / 'examples/tiny_plan.json'
    out = tmp_path / request.param
    if request.param == 'phy':
        phy_ir._window_kit(plan, out, [0, 0, 345.6, 345.6])
    else:
        pytest.importorskip('scipy')  # infra_pg.estimate solves the window with scipy.sparse
        p = D.S.Plan(D.S.load(plan), plan)
        grid = [{'layer': x, 'width_um': .48, 'pitch_um': 8.64,
                 'offset_um': 4.32, 'nets': ['VDD', 'VSS']} for x in ('M8', 'M9')]
        infra_pg.window_kit(p, plan.parent, {'grid': grid}, out, 'tiny', [0, 0, 345.6, 345.6])
    text = (out / 'psm/psm.tcl').read_text()
    return text[text.index('foreach n {VDD VSS} { if {[catch {check_power_grid'):]


@pytest.mark.parametrize('fail,expected', [('none', 0), ('check', 1), ('solve', 1)])
def test_window_tool_failure_returns_nonzero_without_done(generated_tail, fail, expected, tmp_path):
    fixture = f'set failure {fail}\n' + r'''
set t0 [clock seconds]
proc check_power_grid {args} {if {$::failure eq "check"} {error "disconnected PG fixture"}}
proc analyze_power_grid {args} {if {$::failure eq "solve"} {error "solver fixture"}}
'''
    script = tmp_path / 'gate.tcl'
    script.write_text(fixture + generated_tail)
    result = subprocess.run(['tclsh', str(script)], text=True, capture_output=True)
    assert result.returncode == expected, result.stdout + result.stderr
    assert ('OT_DONE' in result.stdout) == (fail == 'none')
    assert ('OT_PG_CHECK_FAIL' in result.stdout) == (fail == 'check')
    assert ('OT_PSM_FAIL' in result.stdout) == (fail == 'solve')
