"""HBM standalone kits must stage and run RTL lint before any synthesis work."""
import os
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]
GEN = ROOT / 'physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py'
RUN = ROOT / 'physical/die_plan/hbm_arch_cores/run_kit_hbm.sh'


def test_hbm_generator_stages_real_lint_tool(tmp_path):
    lines = [line.strip() for line in GEN.read_text().splitlines()
             if 'shutil.copyfile(TOOL / "rtl_lint.py"' in line]
    assert len(lines) == 1
    exec(compile('\n'.join(lines), str(GEN), 'exec'),
         dict(shutil=shutil, TOOL=ROOT / 'tools/die_plan', kd=tmp_path))
    assert (tmp_path / 'rtl_lint.py').read_bytes() == (ROOT / 'tools/die_plan/rtl_lint.py').read_bytes()


@pytest.mark.parametrize('outcome', ['PASS', 'FAIL', 'MISSING'])
def test_actual_runner_lint_prefix_fails_closed_before_synthesis(tmp_path, outcome):
    source = RUN.read_text()
    line = next(line for line in source.splitlines() if 'python3 -I /work/rtl_lint.py /work' in line)
    assert source.index(line) < source.index('$M synth')
    # Execute the actual inner-container gate fragment, with only its mount
    # translated into the isolated test kit. No synthetic production logic.
    command = line.rstrip().removesuffix(chr(92)).strip()
    command = command.replace(chr(92) + '$', '$').replace('/work', str(tmp_path))
    if outcome != 'MISSING':
        (tmp_path / 'rtl_lint.py').write_text(f'print("{outcome}")\nraise SystemExit({int(outcome == "FAIL")})\n')
    marker = tmp_path / 'synthesis_called'
    result = subprocess.run(['bash', '-c', command + '\ntouch ' + str(marker)],
                            env=dict(os.environ, HUID=str(os.getuid()), HGID=str(os.getgid())),
                            capture_output=True, text=True)
    if outcome == 'PASS':
        assert result.returncode == 0 and marker.exists()
        assert not (tmp_path / 'FAIL_PREFLOOR').exists()
    else:
        assert result.returncode == 8 and not marker.exists()
        assert 'FAIL_PREFLOOR rtl_lint' in (tmp_path / 'FAIL_PREFLOOR').read_text()
