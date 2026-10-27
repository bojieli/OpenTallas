"""Exercise generated shell runners: logging and later corners cannot hide failure."""
import os
from pathlib import Path
import subprocess
import sys
import pytest

sys.path.insert(0, str(Path(__file__).parent))
import die_trial as D


def execute(tmp_path, codes):
    fake = tmp_path / 'bin'
    fake.mkdir()
    docker = fake / 'docker'
    docker.write_text('''#!/bin/bash
if [ "$1" = info ]; then exit 0; fi
if [ "$1" = image ]; then echo FAKE_IMAGE; exit 0; fi
while [ "$1" != bash ]; do shift; done
exec "$@"
''')
    docker.chmod(0o755)
    tool = fake / 'tool'
    tool.write_text('#!/bin/bash\necho "ran $CORNER"\ncase "$CORNER" in\n' +
        ''.join(f'{corner}) exit {rc};;\n' for corner, rc in codes.items()) + 'esac\n')
    tool.chmod(0o755)
    stages = [(f'CORNER={c} {tool}', str(tmp_path / f'{c}.log')) for c in codes]
    runner = tmp_path / 'run.sh'
    runner.write_text(D.run_sh('probe', 1, 1, D.logged_stages(stages)))
    env = {**os.environ, 'PATH': str(fake) + ':' + os.environ['PATH'],
           'HUID': str(os.getuid()), 'HGID': str(os.getgid())}
    # The fake Docker executes the exact generated nested shell; it launches no
    # container or design tool. The generated source, status capture and cleanup run.
    result = subprocess.run(['bash', str(runner)], env=env, text=True, capture_output=True)
    return result, {c: (tmp_path / f'{c}.log').read_text() for c in codes}


@pytest.mark.parametrize('tt,ff,expected', [(0, 0, 0), (7, 0, 7), (0, 9, 9), (7, 9, 7)])
def test_both_corners_run_and_first_failure_survives(tmp_path, tt, ff, expected):
    result, logs = execute(tmp_path, {'TT': tt, 'FF': ff})
    assert result.returncode == expected, result.stdout + result.stderr
    assert logs['TT'] == f'ran TT\nEXIT {tt}\n'
    assert logs['FF'] == f'ran FF\nEXIT {ff}\n'
    assert f'exit {expected}' in (tmp_path / 'probe.image.txt').read_text()


def test_grt_logging_preserves_nonzero_tool_status(tmp_path):
    result, logs = execute(tmp_path, {'GRT': 23})
    assert result.returncode == 23, result.stdout + result.stderr
    assert logs['GRT'] == 'ran GRT\nEXIT 23\n'
