# Source-only audit used for independent_main_tests.log; run from clean repo root.
# Invocation: PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=tools python3 this_file.py
import sys,json,os
from pathlib import Path
root=Path.cwd().resolve();blocked=[];subprocesses=[]
def audit(event,args):
    if event=='subprocess.Popen':
        subprocesses.append(repr(args));raise RuntimeError('Independent source replay forbids real subprocesses')
    if event=='open' and isinstance(args[0],(str,bytes)):
        p=Path(os.fsdecode(args[0])).resolve()
        if (str(p).startswith('/home/ubuntu/w17') or str(p).startswith('/tmp/opentallas')) and not p.is_relative_to(root):
            blocked.append(str(p));raise RuntimeError('Private ROOT read forbidden: '+str(p))
sys.addaudithook(audit)
import pytest
code=pytest.main(['-q','-p','w17_D1_portable_pytest','tests/test_w17_D1_event_ledger.py','tests/test_w17_D1_frozen_package.py','tests/test_w17_D1_materialized_prerequisites.py','tests/test_w17_D1_PC24_inputs.py','tests/test_w17_owner_progress_resource_r2.py','tests/test_w17_owner_progress_archival_closure.py'])
print(json.dumps(dict(returncode=code,private_ROOT_attempts=blocked,actual_subprocess_attempts=subprocesses,independent_checkout=str(root))))
raise SystemExit(code)
