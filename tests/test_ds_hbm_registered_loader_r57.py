"""Actual retained loader/class regressions; no substitute class or arithmetic."""
import subprocess,sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
BASE="import sys;from pathlib import Path;sys.path.insert(0,str(Path.cwd()/'tools'));"

def run(script):
    p=subprocess.run([sys.executable,'-c',BASE+script],cwd=ROOT,capture_output=True,text=True)
    assert p.returncode==0,p.stdout+p.stderr


def test_original_failure_then_actual_registered_class_constructor(tmp_path):
    run('''
import inspect,json,tempfile
import ds_hbm_source_prefix_r45 as old
m=old.sagan()
try:inspect.getsource(m.NativeExecution)
except TypeError:pass
else:raise AssertionError('historical failure not reproduced')
import ds_hbm_registered_loader_r57 as new
new.install();a=old.sagan()
import ds_hbm_source_prefix_r39 as r39
import ds_hbm_source_prefix_r43 as r43
assert a is r39.sagan() is r43.sagan()
assert sys.modules[a.NativeExecution.__module__] is a
assert Path(inspect.getsourcefile(a.NativeExecution)).resolve()==new.SOURCE.resolve()
for cls in old.driver_class().__mro__:
 if cls is not object:assert inspect.getsource(cls)
# Invoke the actual retained constructor, not a stand-in. Its exact artifact
# guard must refuse wrong dispatch before any provider/token initialization.
with tempfile.TemporaryDirectory() as d:
 p=Path(d)/'wrong_dispatch';p.write_bytes(b'wrong')
 try:a.NativeExecution({}, {}, None, 'revision',1,[],native_artifact_path=p,dispatch_artifact_path=p)
 except ValueError as e:assert 'exact corrected native dispatch' in str(e)
 else:raise AssertionError('actual constructor weakened')
''')


def test_conflicting_module_refuses_without_overwrite():
    run('''
import types
import ds_hbm_registered_loader_r57 as new
bad=types.ModuleType(new.NAME);bad.__file__='wrong';sys.modules[new.NAME]=bad
try:new.registered_sagan()
except ValueError as e:assert 'conflicting' in str(e)
else:raise AssertionError('conflict accepted')
assert sys.modules[new.NAME] is bad
''')


def test_wrong_source_hash_refuses_before_registration():
    run('''
import ds_hbm_registered_loader_r57 as new
new.SHA='0'*64
try:new.registered_sagan()
except ValueError as e:assert 'exact retained' in str(e)
else:raise AssertionError('wrong pin accepted')
assert new.NAME not in sys.modules
''')
