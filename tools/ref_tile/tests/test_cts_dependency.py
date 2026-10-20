"""Execute the emitted stage orchestration with process stubs, preserving shell RCs."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pre_route_gate as P


def run_stages(cts_rc, cts=True, trial=True):
    start = P.REMOTE_SH.index('if [ "{CTS}" = 1 ]; then')
    script = P.REMOTE_SH[start:]
    # The remaining section has only substitutions and escaped shell braces.
    import string
    names = {name: 'fixture' for _, name, _, _ in string.Formatter().parse(script) if name}
    names.update(CTS=int(cts), TRIAL=int(trial), IMG='fixture', KIT='fixture', GRTX='')
    script = script.format(**names)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / 'bin').mkdir()
        for name in ('python3', 'docker'):
            p = root / 'bin' / name
            p.write_text('#!/bin/bash\nprintf "%s %s\\n" "${0##*/}" "$*" >> "$JOURNAL"\n')
            p.chmod(0o755)
        prelude = '''set -uo pipefail
R="$TEST_ROOT"; C="$R/work"; B="$C/base"; NB=base
mkdir -p "$B"
ot_capped() {
  echo "$1" >> "$JOURNAL"
  if [[ "$1" == gate_cts_* ]]; then echo original_cts_diagnostic; return "$TEST_CTS_RC"; fi
  return 0
}
ot_layout() { echo "layout $*" >> "$JOURNAL"; }
'''
        proc = subprocess.run(['bash', '-c', prelude + script], text=True, capture_output=True,
                              env={**os.environ, 'PATH': str(root/'bin') + ':' + os.environ['PATH'],
                                   'TEST_ROOT': tmp, 'JOURNAL': str(root/'calls'), 'TEST_CTS_RC': str(cts_rc)})
        calls = (root/'calls').read_text()
        original = (root/'cts.log').read_text() if cts else None
        return proc, calls, original


def test_failed_cts_preserves_original_failure_and_skips_all_consumers():
    proc, calls, log = run_stages(23)
    assert proc.returncode == 0  # the existing terminal/parser path records stage failure
    assert 'GATE_CTS_RC=23' in proc.stdout
    for stage in ('CK', 'PATH_CLASSES', 'PLACED_LAYOUT', 'GRT'):
        assert f'GATE_{stage}_SKIPPED=cts_failed' in proc.stdout
    assert calls.count('gate_cts_') == 1
    assert 'gate_grt_' not in calls
    assert 'ck_insertion.py' not in calls and 'path_classes.tcl' not in calls
    assert 'layout ' not in calls
    assert log == 'original_cts_diagnostic\n'


def test_successful_cts_retains_native_consumers_and_trial_route():
    proc, calls, log = run_stages(0)
    assert proc.returncode == 0, proc.stderr
    assert 'GATE_CTS_RC=0' in proc.stdout and 'GATE_GRT_RC=0' in proc.stdout
    assert '_SKIPPED=' not in proc.stdout
    assert calls.count('gate_cts_') == 1 and calls.count('gate_grt_') == 1
    assert 'ck_insertion.py' in calls and 'path_classes.tcl' in calls
    assert calls.index('gate_cts_') < calls.index('ck_insertion.py') < calls.index('gate_grt_')
    assert log == 'original_cts_diagnostic\n'


def test_trial_without_requested_cts_keeps_existing_make_dependency_path():
    proc, calls, _ = run_stages(23, cts=False)
    assert proc.returncode == 0, proc.stderr
    assert 'gate_cts_' not in calls and calls.count('gate_grt_') == 1
    assert '_SKIPPED=' not in proc.stdout
