from pathlib import Path
import os, subprocess, tempfile
import pytest
from tools.die_plan import synth_diagnostics as tool

SOURCE='#!/bin/bash\nset -u -eo pipefail\ntouch $2\n$YOSYS_EXE $YOSYS_FLAGS -c $1\necho FINISHED\n'

def test_anchored_idempotent_and_fail_closed():
    result=tool.patch(SOURCE)
    assert tool.patch(result)==result
    with pytest.raises(ValueError):tool.patch(SOURCE.replace('-c $1','-s $1'))
    with pytest.raises(ValueError):tool.patch(result.replace(' -l ', ' -oops '))

@pytest.mark.parametrize('exit_code',[0,7])
def test_full_diagnostic_surfaced_and_original_exit_preserved(tmp_path,exit_code):
    fake=tmp_path/'yosys'
    fake.write_text('#!/bin/bash\nwhile [ $# -gt 0 ]; do if [ "$1" = -l ]; then shift; echo "bad.sv:1: error: unknown module missing_child" > "$1"; fi; shift; done\nexit '+str(exit_code)+'\n')
    fake.chmod(0o755)
    script=tmp_path/'synth.sh';script.write_text(tool.patch(SOURCE))
    env=dict(os.environ,YOSYS_EXE=str(fake),YOSYS_FLAGS='-v 3')
    result=subprocess.run(['bash',str(script),'unused',str(tmp_path/'stage.log')],env=env,text=True,capture_output=True)
    assert result.returncode==exit_code
    if exit_code:
        assert 'unknown module missing_child' in result.stderr
        assert 'OT_SYNTH_DIAGNOSTICS exit=7' in result.stderr
        assert 'FINISHED' not in result.stdout
    else:
        assert 'FINISHED' in result.stdout
        assert 'OT_SYNTH_DIAGNOSTICS exit=' not in result.stderr
