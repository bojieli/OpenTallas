"""Staged face guards remain self-contained under the production -I entrypoint."""
import os
import shutil
import subprocess
import sys
from pathlib import Path
import signoff as S
HERE=Path(__file__).parent

def test_isolated_guard_uses_its_staged_helper_not_working_directory(tmp_path):
    kit=tmp_path/'kit';other=tmp_path/'other';kit.mkdir();other.mkdir()
    for name in ('face_guard.py','hard_landing.py'):shutil.copyfile(HERE/name,kit/name)
    (other/'hard_landing.py').write_text("raise RuntimeError('wrong cohort')")
    code=(f"import runpy,pathlib;runpy.run_path({str(kit/'face_guard.py')!r},run_name='guard_import_test');"
          f"import hard_landing;assert pathlib.Path(hard_landing.__file__)==pathlib.Path({str(kit/'hard_landing.py')!r})")
    result=subprocess.run([sys.executable,'-I','-c',code],cwd=other,
                          env=dict(os.environ,PYTHONPATH=str(other)),capture_output=True,text=True)
    assert result.returncode==0,result.stderr

def test_landing_helper_travels_with_same_source_cohort_when_present(tmp_path):
    for name in S.SIGNOFF_BUNDLE:(tmp_path/name).write_text('same source cohort')
    helper=tmp_path/'hard_landing.py';helper.write_text('same source cohort helper')
    assert S.signoff_bundle_sources(tmp_path)['hard_landing.py']==helper
    helper.unlink()
    assert 'hard_landing.py' not in S.signoff_bundle_sources(tmp_path)
