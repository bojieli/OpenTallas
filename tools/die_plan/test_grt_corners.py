"""Execute the generated GRT command selection without running implementation tools."""
import os
from pathlib import Path
import re
import subprocess
import sys

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import core_flow
import gen_phys

ROOT = HERE.parent.parent


@pytest.mark.parametrize('runner', [
    core_flow.FF_GRT_STEP,
    gen_phys.RUN_KIT,
    (ROOT / 'physical/die_plan/hbm_arch_cores/run_kit_hbm.sh').read_text(),
], ids=['legacy-core', 'partition', 'hbm-core'])
@pytest.mark.parametrize('config,expected', [
    ('export CORNERS = tc bc\n', ['grt', 'HOLD_SLACK_MARGIN=5']),
    ('export CORNERS = tc\n', ['grt', 'CORNER=BC', 'CORNERS=bc', 'HOLD_SLACK_MARGIN=5']),
    ('', ['grt', 'CORNER=BC', 'CORNERS=bc', 'HOLD_SLACK_MARGIN=5']),
])
def test_grt_uses_declared_mcmm_corners(runner, config, expected, tmp_path):
    # Execute exactly the selection and make invocation embedded in each runner.
    start = runner.index("GC='CORNER=BC CORNERS=bc'")
    end = runner.index('rc=', start)
    command = runner[start:end]
    command = re.sub(r'\\+\$', '$', command)
    cfg = tmp_path / 'config.mk'
    cfg.write_text(config)
    command = command.replace('/work/config.mk', str(cfg))
    mock_make = tmp_path / 'make'
    mock_make.write_text('#!/bin/bash\nprintf "%s\\n" "$OT_VCLK_CORNER" "$@"\n')
    mock_make.chmod(0o755)
    proc = subprocess.run(['bash', '-c', command], text=True, capture_output=True,
                          env=dict(os.environ, M=str(mock_make), HM='5'))
    assert proc.returncode == 0, proc.stderr
    # TT setup repair remains available through the kit's tc+bc configuration,
    # while hold still uses the explicitly selected FF virtual-clock reference.
    assert proc.stdout.splitlines() == ['ff', *expected]
