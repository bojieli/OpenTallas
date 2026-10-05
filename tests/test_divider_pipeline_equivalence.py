"""Pipeline changes preserve the certifying divider and Sinkhorn arithmetic."""
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(shutil.which('iverilog') is None, reason='iverilog unavailable')
@pytest.mark.parametrize('sinkhorn,divider', [(False, 1), (True, 0), (True, 1)])
def test_pipelined_arithmetic(tmp_path, sinkhorn, divider):
    names = ['rtl/ot_fp32_rne_pkg.sv', 'rtl/abi3/ot_a3_fp32_div_rne.sv',
             'rtl/abi3/ot_a3_fp32_div_rne_pipe.sv']
    top = 'tb_a3_fp32_div_pipe_equiv'
    params = []
    if sinkhorn:
        top = 'tb_a3_hc_sinkhorn20_pipe_equiv'
        names += ['rtl/proto/ot_fp32_add_positive_rne_pipe.sv',
                  'rtl/abi3/ot_a3_hc_sinkhorn20_rne.sv',
                  'rtl/abi3/ot_a3_hc_sinkhorn20_rne_pipe.sv']
        params = [f'-P{top}.PIPELINED_DIVIDER={divider}']
    names.append(f'rtl/test/{top}.sv')
    verilator = Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator'
    if sinkhorn and verilator.is_file():
        command = [str(verilator), '--binary', '--timing', '-j', '4', '-Wno-fatal',
                   '--top-module', top, f'-GPIPELINED_DIVIDER={divider}',
                   '--Mdir', str(tmp_path/'obj'), '-o', 'sim', *[str(ROOT/n) for n in names]]
        subprocess.run(command, check=True, capture_output=True, text=True, timeout=120)
        run = [str(tmp_path/'obj/sim')]
    else:
        subprocess.run(['iverilog', '-g2012', '-s', top, *params, '-o', str(tmp_path/'sim'),
                        *[str(ROOT/n) for n in names]], check=True, capture_output=True, text=True, timeout=30)
        run = ['vvp', str(tmp_path/'sim')]
    result = subprocess.run(run, capture_output=True, text=True, timeout=300)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'FAILURES 0' in result.stdout
    assert 'EQUIVALENT' in result.stdout
    assert f'CASES {36 if sinkhorn else 673}' in result.stdout


@pytest.mark.skipif(shutil.which('iverilog') is None, reason='iverilog unavailable')
def test_divider_reset_and_output_backpressure(tmp_path):
    top = 'tb_a3_fp32_div_pipe_protocol'
    subprocess.run(['iverilog', '-g2012', '-s', top, '-o', str(tmp_path/'sim'),
                    str(ROOT/'rtl/ot_fp32_rne_pkg.sv'),
                    str(ROOT/'rtl/abi3/ot_a3_fp32_div_rne_pipe.sv'),
                    str(ROOT/f'rtl/test/{top}.sv')],
                   check=True, capture_output=True, text=True, timeout=30)
    run = subprocess.run(['vvp', str(tmp_path/'sim')], capture_output=True, text=True, timeout=30)
    assert run.returncode == 0, run.stdout + run.stderr
    assert 'PASS divider protocol reset_phases=4 stalled_results=8 replacement=1' in run.stdout


@pytest.mark.parametrize('divider', [0, 1])
def test_sinkhorn_reset_and_output_backpressure(tmp_path, divider):
    verilator = Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator'
    if not verilator.is_file():
        pytest.skip('pinned Verilator unavailable')
    top = 'tb_a3_hc_sinkhorn20_pipe_protocol'
    names = ['rtl/ot_fp32_rne_pkg.sv', 'rtl/abi3/ot_a3_fp32_div_rne.sv',
             'rtl/abi3/ot_a3_fp32_div_rne_pipe.sv',
             'rtl/proto/ot_fp32_add_positive_rne_pipe.sv',
             'rtl/abi3/ot_a3_hc_sinkhorn20_rne.sv',
             'rtl/abi3/ot_a3_hc_sinkhorn20_rne_pipe.sv', f'rtl/test/{top}.sv']
    command = [str(verilator), '--binary', '--timing', '-j', '4', '-Wno-fatal',
               '--top-module', top, f'-GPIPELINED_DIVIDER={divider}',
               '--Mdir', str(tmp_path/'obj'), '-o', 'sim', *[str(ROOT/n) for n in names]]
    subprocess.run(command, check=True, capture_output=True, text=True, timeout=120)
    result = subprocess.run([str(tmp_path/'obj/sim')], capture_output=True, text=True, timeout=120)
    (tmp_path/'simulation.log').write_text(result.stdout + result.stderr)
    assert result.returncode == 0, result.stdout + result.stderr
    assert f'PASS Sinkhorn protocol divider={divider} resets=9 recoveries=9 stalls=90' in result.stdout
