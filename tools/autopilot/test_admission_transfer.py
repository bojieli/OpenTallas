"""Exercise the embedded bootstrap without starting any physical runner."""
import ast
import base64
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import subprocess

TREE = ast.parse(Path(__file__).with_name('autopilot.py').read_text())
BOOTSTRAP = next(ast.literal_eval(n.value) for n in TREE.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'ADMISSION_BOOTSTRAP' for t in n.targets))

class TransferTest(unittest.TestCase):
    def exercise(self, failures=0, wrong=False):
        with tempfile.TemporaryDirectory(prefix='admission-') as temp:
            dest = Path(temp)/'bundle'
            # Preserve the production path check while using an isolated test directory.
            code = BOOTSTRAP.replace('if not str(dest).startswith("/"+"srv/opentallas-scratch") or "/claude/" not in str(dest):', 'if False:')
            calls = []; executions = []
            class Source:
                stdout = io.BytesIO()
                def wait(self): return 0
            def extract(args, **kwargs):
                calls.append(args)
                if len(calls) <= failures: return subprocess.CompletedProcess(args, 2)
                target=Path(args[2]); (target/'BUNDLE.json').write_text(json.dumps({'sha256':'wrong' if wrong else 'wanted'}))
                return subprocess.CompletedProcess(args, 0)
            def execute(*args):
                executions.append(args)
                raise SystemExit(0)
            meta=base64.b64encode(json.dumps(dict(dir=str(dest),sha256='wanted',source_host='hub')).encode()).decode()
            output=io.StringIO()
            with patch('sys.argv',['bootstrap',meta,'runner','kit','route']), patch('subprocess.Popen',side_effect=lambda *a,**kw: type('Source',(),{'stdout':io.BytesIO(),'wait':lambda self:0})()), patch('subprocess.run',side_effect=extract), patch('os.execv',side_effect=execute), contextlib.redirect_stdout(output):
                with self.assertRaises(SystemExit) as result: exec(compile(code,'bootstrap','exec'),{})
            return result.exception.code,len(calls),len(executions),output.getvalue()
    def test_transient_transport_then_exec_once(self):
        rc,n,executions,out=self.exercise(failures=1)
        self.assertEqual((rc,n,executions),(0,2,1)); self.assertIn('transport retry 1/3',out)
    def test_transport_failure_never_executes(self):
        rc,n,executions,out=self.exercise(failures=9)
        self.assertEqual((rc,n,executions),(3,3,0)); self.assertIn('after 3 attempts',out)
    def test_invalid_version_is_not_retried(self):
        rc,n,executions,out=self.exercise(wrong=True)
        self.assertEqual((rc,n,executions),(3,1,0)); self.assertIn('version differs',out)

if __name__ == '__main__': unittest.main()
