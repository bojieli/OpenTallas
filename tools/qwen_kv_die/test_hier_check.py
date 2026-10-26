"""Exercise the real shell checker against controlled tool exit/output cases."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
CHECKER = ROOT / 'tools/qwen_kv_die/hier_check.sh'
ORIGINAL = ROOT / 'results/arch/codex_hier_check_exit_2140/original_hier_check.sh'


class HierarchyExit(unittest.TestCase):
    def run_checker(self, tool, checker=CHECKER, timeout_seconds=None):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'bin').mkdir(); (root/'rtl').mkdir()
            (root/'tiles.sv').write_text('module top; endmodule\n')
            (root/'rtl/needed.sv').write_text('module needed; endmodule\n')
            yosys = root/'bin/yosys'; yosys.write_text('#!/bin/bash\n'+tool); yosys.chmod(0o755)
            timeout = root/'bin/timeout'
            timeout.write_text('#!/bin/bash\nprintf "%s\\n" "$1" >> "$HIER_TIMEOUT_TRACE"\nshift\nexec "$@"\n')
            timeout.chmod(0o755)
            env = dict(os.environ, PATH=str(root/'bin')+':'+os.environ['PATH'], EXTRA_FILES='',
                       HIER_TIMEOUT_TRACE=str(root/'timeout_calls'))
            env.pop('HIER_CHECK_TIMEOUT_SECONDS', None)
            if timeout_seconds is not None: env['HIER_CHECK_TIMEOUT_SECONDS'] = str(timeout_seconds)
            result = subprocess.run(['bash', str(checker), str(root), 'tiles.sv'], text=True,
                                    capture_output=True, env=env)
            trace = root/'timeout_calls'
            result.timeout_calls = trace.read_text().splitlines() if trace.exists() else []
            return result

    def test_timeout_without_error_text_never_passes(self):
        tool = 'echo "partial hierarchy output before timeout"; exit 124\n'
        old = self.run_checker(tool, ORIGINAL)
        self.assertEqual(old.returncode, 0)
        self.assertIn('hierarchy -check PASS', old.stdout)
        new = self.run_checker(tool)
        self.assertEqual(new.returncode, 124)
        self.assertIn('HIERARCHY_TOP top=top iteration=1 exit=124', new.stdout)
        self.assertIn('partial hierarchy output before timeout', new.stdout)
        self.assertNotIn('hierarchy -check PASS', new.stdout)

    def test_nonzero_without_error_text_preserves_status_and_output(self):
        result = self.run_checker('echo "tool failed without diagnostic keyword"; exit 7\n')
        self.assertEqual(result.returncode, 7)
        self.assertEqual(result.timeout_calls, [])
        self.assertIn('tool failed without diagnostic keyword', result.stdout)
        self.assertNotIn('hierarchy -check PASS', result.stdout)

    def test_ordinary_success_preserves_output(self):
        result = self.run_checker('echo "ordinary hierarchy output"; exit 0\n')
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.timeout_calls, [])
        self.assertIn('ordinary hierarchy output', result.stdout)
        self.assertIn('HIERARCHY_TOP top=top iteration=1 exit=0', result.stdout)
        self.assertIn('hierarchy -check PASS: 1 tile modules', result.stdout)

    def test_explicit_bounded_diagnostic_preserves_timeout_status(self):
        result = self.run_checker('echo "bounded partial output"; exit 124\n', timeout_seconds=5)
        self.assertEqual(result.returncode, 124)
        self.assertEqual(result.timeout_calls, ['5'])
        self.assertIn('bounded partial output', result.stdout)
        self.assertNotIn('hierarchy -check PASS', result.stdout)

    def test_explicit_unbounded_success_avoids_timeout(self):
        result = self.run_checker('echo "unbounded success"; exit 0\n', timeout_seconds=0)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.timeout_calls, [])

    def test_error_text_still_refuses_even_with_zero_status(self):
        result = self.run_checker('echo "ERROR: malformed design"; exit 0\n')
        self.assertEqual(result.returncode, 1)
        self.assertNotIn('hierarchy -check PASS', result.stdout)

    def test_missing_module_resolution_still_requires_successful_retry(self):
        tool = '''case "$*" in
  *rtl/needed.sv*) echo 'resolved hierarchy output'; exit 0;;
  *) echo "ERROR: Module \`\\needed' referenced in module top"; exit 1;;
esac
'''
        result = self.run_checker(tool)
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        self.assertIn('add rtl/needed.sv for needed', result.stdout)
        self.assertIn('resolved hierarchy output', result.stdout)
        self.assertIn('hierarchy -check PASS: 1 tile modules, 2 files', result.stdout)


if __name__ == '__main__':
    unittest.main()
