import ast
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import native_build_unlimited_exec as E


class FutureLaunchers(unittest.TestCase):
    def test_kernel_entry_rejects_each_inherited_finite_limit(self):
        good = {name: (-1, -1) for name in ['FSIZE', 'AS', 'CPU']}
        self.assertEqual(E.prepare_argv(['--', 'make', '-j24'], good), ['make', '-j24'])
        for name in good:
            for pair in [(900, 900), (-1, 900), (900, -1)]:
                bad = dict(good); bad[name] = pair
                with self.subTest(name=name, pair=pair), self.assertRaises(ValueError):
                    E.prepare_argv(['--', 'make'], bad)
        with self.assertRaises(ValueError): E.prepare_argv(['make'], good)

    def test_kernel_entry_rejects_downstream_wrappers(self):
        good = {name: (-1, -1) for name in ['FSIZE', 'AS', 'CPU']}
        for command in [['timeout', '900', 'make'], ['prlimit', '--cpu=900', 'make'],
                        ['prlimit', '--as=3221225472', 'g++'],
                        ['prlimit', '--fsize=1073741824', 'g++']]:
            with self.subTest(command=command), self.assertRaises(ValueError):
                E.prepare_argv(['--'] + command, good)

    def test_entry_has_no_limit_or_job_mutation_during_preflight(self):
        t = ast.parse((ROOT / 'tools/native_build_unlimited_exec.py').read_text())
        calls = {n.func.attr for n in ast.walk(t) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
        self.assertNotIn('setrlimit', calls)
        self.assertNotIn('kill', calls)

    def test_native_transport_unlimited_and_preserves_existing_root(self):
        d = ROOT / 'results/uarch/native_build_future_launcher_audit_20261002/launchers'
        text = (d / 'remote_gate_native_unlimited.base.py').read_text()
        ast.parse(text)
        for required in ['--ulimit cpu=-1:-1', '--ulimit as=-1:-1',
                         '--ulimit fsize=-1:-1', '--cpu=unlimited:unlimited',
                         '--as=unlimited:unlimited', 'tools/native_build_unlimited_exec.py']:
            self.assertIn(required, text)
        for prohibited in ['git clean -fdq', 'checkout -q -f', 'rm -rf {q(cwd)}']:
            self.assertNotIn(prohibited, text)
        self.assertIn('test ! -e {q(cwd)}', text)
        self.assertIn('rev-parse HEAD', text)

    def test_native_guard_retains_shared_reservations_and_user_holds(self):
        d = ROOT / 'results/uarch/native_build_future_launcher_audit_20261002/launchers'
        text = (d / 'remote_gate_native_unlimited_guarded.py').read_text()
        ast.parse(text)
        self.assertIn("R=Path('/tmp/claude-1000/queue/fleet-admission-guard-20261002')", text)
        self.assertIn("vm.get('disabled') or vm.get('admission_hold_owner')=='user'", text)
        self.assertIn('validate_model(plan)', text)
        self.assertIn('validate_native_argv(os.sys.argv[1:])', text)
        self.assertIn("plan['memory_bytes'] != plan['memory_gib'] * (1<<30)", text)
        self.assertIn("plan['workers'] != plan['threads']", text)
        self.assertIn('tools/native_build_completion_policy_r2.py', text)


if __name__ == '__main__':
    unittest.main()
