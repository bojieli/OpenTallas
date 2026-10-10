"""Real-domain reset behavior; test PLL is excluded from production source."""
from pathlib import Path
import shutil
import subprocess
import pytest

ROOT = Path(__file__).resolve().parents[1]
CONTROL = ROOT / 'rtl/hbm_accel/control'


def simulate(tmp_path, mutation=False):
    source = (CONTROL / 'ot_hbm_clock_reset_boundary.sv').read_text()
    if mutation:
        source = source.replace('por_n & pll_reset_n & pll_lock', 'por_n & pll_reset_n')
    candidate = tmp_path / 'candidate.sv'
    candidate.write_text(source)
    executable = tmp_path / 'tb.vvp'
    subprocess.run(['iverilog', '-g2012', '-s', 'tb', '-o', str(executable),
                    str(candidate), str(CONTROL / 'ot_hbm_reset_seq.sv'),
                    str(ROOT / 'tests/rtl/tb_hbm_clock_reset_boundary.sv')], check=True,
                   capture_output=True, text=True)
    return subprocess.run(['vvp', str(executable)], capture_output=True, text=True)


@pytest.mark.skipif(not shutil.which('iverilog'), reason='iverilog unavailable')
def test_all_endpoints_release_only_on_real_destination_edges(tmp_path):
    result = simulate(tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'PASS clock/reset boundary: 17 endpoints' in result.stdout


@pytest.mark.skipif(not shutil.which('iverilog'), reason='iverilog unavailable')
def test_negative_control_missing_raw_lock_veto_fails(tmp_path):
    result = simulate(tmp_path, mutation=True)
    assert result.returncode != 0
    assert 'release before acquisition' in result.stdout or 'endpoint' in result.stdout


@pytest.mark.skipif(not shutil.which('iverilog'), reason='iverilog unavailable')
def test_production_sources_elaborate_with_unimplemented_analog_macro(tmp_path):
    subprocess.run(['iverilog', '-g2012', '-s', 'ot_hbm_clock_reset_boundary',
                    '-o', str(tmp_path/'boundary.vvp'),
                    str(CONTROL/'ot_hbm_pll_bb.sv'),
                    str(CONTROL/'ot_hbm_clock_reset_boundary.sv'),
                    str(CONTROL/'ot_hbm_reset_seq.sv')], check=True, capture_output=True)
    production = (CONTROL/'ot_hbm_pll_bb.sv').read_text()
    assert '(* blackbox *)' in production
    assert 'always' not in production and 'assign' not in production
