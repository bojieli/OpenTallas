"""lep ri RIP table: RTL selectors, plan types, kit mismatch and the per-beat trace check (LEPFLF traces)."""
import json
import sys
from pathlib import Path

import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from layer_prog import lep_rip as L

ROOT = Path(__file__).resolve().parents[3]
T = ROOT / 'results/token_pass/s81_lep_rip_1124'


def rd(n):
    return [int(x) for x in (T / f'rit_{n}.txt').read_text().split()]


def test_rtl_selectors():
    sel, default = L.selectors()
    assert sel['OT_S81SL_LEP_RIP1'] == 1 and sel['OT_S81SL_LEP_RIP3'] == 3 and default == 0


def test_type_rip():
    assert L.lep_ri_rip([]) == 0
    assert L.lep_ri_rip(['OT_S81SL_LEP_CRP2', 'OT_S81SL_LEP_WREP5']) == 0
    assert L.lep_ri_rip(['OT_S81SL_LEP_CRP2', 'OT_S81SL_LEP_RIP3', 'OT_S81SL_LEP_ROS3']) == 3
    assert L.lep_ri_rip(['OT_S81SL_LEP_RIP=2']) == 2


def test_c8_table():
    plan = json.loads((T / 'c8_lep_types.json').read_text())
    assert L.table(plan) == json.loads((T / 'c8_lep_rip.json').read_text())


def test_kit_must_match_plan():
    assert L.check_kit(['OT_S81SL_LEP_RIP3'], ['OT_S81SL_LEP_RIP3', 'OT_S81SL_LEP_CRP2']) == 3
    with pytest.raises(ValueError):
        L.check_kit([], ['OT_S81SL_LEP_RIP3'])


@pytest.mark.parametrize('name,defines,rip', [
    ('rip1', ['OT_S81SL_LEP_RIP1'], 1), ('rip3', ['OT_S81SL_LEP_RIP3'], 3),
    ('kit_mu_LP_t2', ['OT_S81SL_LEP_CRP2', 'OT_S81SL_LEP_WREP5', 'OT_S81SL_LEP_RIP3', 'OT_S81SL_LEP_ROS3'], 3),
    ('crp2_wrep5_ros3', ['OT_S81SL_LEP_CRP2', 'OT_S81SL_LEP_WREP5', 'OT_S81SL_LEP_ROS3'], 0)])
def test_measured_traces_match_table(name, defines, rip):
    assert L.check_trace(rd('rip0'), rd(name), defines) == rip


@pytest.mark.parametrize('name,wrong', [('rip3', ['OT_S81SL_LEP_RIP1']), ('rip1', []), ('kit_mu_LP_t2', ['OT_S81SL_LEP_CRP2']),
                                        ('crp2_wrep5_ros3', ['OT_S81SL_LEP_RIP3'])])
def test_wrong_rip_fails(name, wrong):
    with pytest.raises(ValueError):
        L.check_trace(rd('rip0'), rd(name), wrong)


def test_kit_config_defines_and_dash_d(tmp_path):
    mk = tmp_path / 'config.mk'
    mk.write_text('export DESIGN_NAME = x\nexport VERILOG_DEFINES = -DSYNTHESIS -DOT_S81SL_LEP_CRP2 -DOT_S81SL_LEP_RIP3\n')
    kd = L.kit_config_defines(mk)
    assert kd == ['SYNTHESIS', 'OT_S81SL_LEP_CRP2', 'OT_S81SL_LEP_RIP3']
    assert L.lep_ri_rip(['-DOT_S81SL_LEP_RIP1']) == 1
    with pytest.raises(ValueError):
        L.check_kit(['OT_S81SL_LEP_CRP2', 'OT_S81SL_LEP_RIP1'], kd)      # J8 lepw_mus_LP t2: kit RIP 3, plan RIP 1


def test_repo_root_env_selects_the_bound_tree(tmp_path):
    import importlib, os, subprocess
    r = tmp_path / 'rtl/dsrom_sys/s81_dv/slice'
    r.mkdir(parents=True)
    r.joinpath('ot_s81sl_slice_lep.sv').write_text(L.RTL.read_text())
    out = subprocess.run([sys.executable, '-I', '-c', 'import sys; sys.path.insert(0, sys.argv[1]); '
                          'from layer_prog import lep_rip; print(lep_rip.RTL)', str(Path(L.__file__).parents[1])],
                         env=dict(os.environ, OT_REPO_ROOT=str(tmp_path)), capture_output=True, text=True, check=True)
    assert out.stdout.strip() == str(r / 'ot_s81sl_slice_lep.sv')
