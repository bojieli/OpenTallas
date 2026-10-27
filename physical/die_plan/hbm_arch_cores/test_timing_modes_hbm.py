"""HBM-CORES-R11 (COORD 2026-10-27 10:37 ruling 2): HBM core kits repair TT setup post-CTS and at GRT, one timing
mode per corner (SIGNOFF-MODES-2 tools/die_plan/kit_modes.py)."""
import importlib.util
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
spec = importlib.util.spec_from_file_location('coregen_modes', HERE / 'gen_core_kit_hbm.py')
coregen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(coregen)
ksp = importlib.util.spec_from_file_location('kit_modes_t', REPO / 'tools/die_plan/kit_modes.py')
km = importlib.util.module_from_spec(ksp)
ksp.loader.exec_module(km)


def mini_kit(kd):
    cfg = ['export DESIGN_NAME = t', 'export SKIP_CTS_REPAIR_TIMING = 1', 'export POST_CTS_TCL = /work/tap_balance.tcl',
           'override export POST_CTS_TCL = /work/f4_chain_leaf.tcl', 'export POST_CTS_TCL = /work/ignored.tcl',
           'export OT_VCLK_TT = 250', 'export OT_VCLK_FF = 202.5', 'export CORNERS = tc bc',
           'export TC_LIB_FILES = a.lib', 'export BC_LIB_FILES = b.lib']
    (kd / 'constraint.sdc').write_text('create_clock -name vclk -period 833\nset_clock_latency -source 250 [get_clocks vclk]\n')
    (kd / 'sdc_lint.json').write_text('{"insertion_ps": 250.0, "insertion_ff_ps": 202.5, "time_unit_ps": 1.0}\n')
    return cfg


def test_post_cts_hook_chains_effective_override(tmp_path):
    cfg = mini_kit(tmp_path)
    r = coregen.post_cts_setup_hook(tmp_path, cfg)
    assert r['previous_post_cts'] == '/work/f4_chain_leaf.tcl'
    assert cfg[-1] == 'override export POST_CTS_TCL = /work/post_cts_setup.tcl'
    assert coregen._effective_hook(cfg, 'POST_CTS_TCL') == '/work/post_cts_setup.tcl'
    t = (tmp_path / 'post_cts_setup.tcl').read_text()
    assert 'source {/work/f4_chain_leaf.tcl}' in t and 'ignored' not in t
    assert 'repair_timing_helper -setup' in t and '-hold' not in t.split('repair_timing_helper')[1].split('\n')[0]


def _run_hook(tmp_path, slack):
    (tmp_path / 'prev.tcl').write_text('lappend ::ev PREV\n')
    t = (tmp_path / 'post_cts_setup.tcl').read_text().replace('/work/f4_chain_leaf.tcl', str(tmp_path / 'prev.tcl'))
    stub = f'''set ::ev {{}}
set ::ws {slack}
proc estimate_parasitics {{args}} {{}}
proc worst_slack {{args}} {{ return $::ws }}
proc repair_timing_helper {{args}} {{ lappend ::ev "RT $args"; set ::ws 1.0 }}
proc detailed_placement {{args}} {{ lappend ::ev DPL }}
proc check_placement {{args}} {{}}
'''
    p = subprocess.run(['tclsh'], input=stub + t + '\nputs "EV $::ev"\n', text=True, capture_output=True, check=True)
    return [ln for ln in p.stdout.splitlines() if ln.startswith(('EV', 'OT_CTS'))]


def test_hook_repairs_setup_only_when_negative(tmp_path):
    cfg = mini_kit(tmp_path)
    coregen.post_cts_setup_hook(tmp_path, cfg)
    out = _run_hook(tmp_path, -20.41)
    assert out[-1] == 'EV PREV {RT -setup} DPL'
    assert 'before: worst setup -20.41' in out[0] and 'after: worst setup 1.00' in out[1]
    assert _run_hook(tmp_path, 5.0)[-1] == 'EV PREV'


def test_stage_two_mode_and_grt_check(tmp_path):
    cfg = mini_kit(tmp_path)
    (tmp_path / 'config.mk').write_text('\n'.join(cfg) + '\n')
    r = coregen.timing_modes_stage(tmp_path, True)
    assert r == dict(mode='two-mode tc setup / BC hold', tt=250.0, ff=202.5)
    for f in ('vclk_ff.sdc', 'orfs_hold_mm.py', 'orfs_hold_mm.tcl', 'kit_modes.py'):
        assert (tmp_path / f).is_file()
    assert km.check(tmp_path, 'grt', session='tc bc', hold_repair=True)['mm'] is True
    # CTS step: setup-only hook is not a hold repair (one mode per corner holds at CTS too)
    assert km.check(tmp_path, 'cts')['hold_repair'] is False


def test_single_mode_grt_opt_out(tmp_path):
    cfg = mini_kit(tmp_path)
    (tmp_path / 'config.mk').write_text('\n'.join(cfg) + '\n')
    r = coregen.timing_modes_stage(tmp_path, False)
    assert r['mode'] == 'FF-only GRT hold' and 'OT_HOLD_MM' not in (tmp_path / 'config.mk').read_text()


def test_run_script_grt_session_checked():
    s = (HERE / 'run_kit_hbm.sh').read_text()
    subprocess.run(['bash', '-n', str(HERE / 'run_kit_hbm.sh')], check=True)
    assert "kit_modes.py check /work --step grt --session 'tc bc' --hold-repair" in s
    assert 'kit_modes.py check /work --step grt --session bc --vclk-corner ff --hold-repair' in s
    assert s.index('orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts') < s.index('$M synth')
