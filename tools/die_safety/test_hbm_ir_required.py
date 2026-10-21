"""Exercise the actual HBM IR stage with terminal/missing artifacts, without OpenROAD."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


class HbmIrRequired(unittest.TestCase):
    def stage(self, odb=False, step_exit=0):
        script = Path(__file__).resolve().parents[1] / 'hbm_die_post_grt.sh'
        stage = script.read_text().split('# ---- 5 IR ----\n', 1)[1].split('# ---- 6 summary', 1)[0]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'grt').mkdir()
            (root / 'src/tools/die_safety').mkdir(parents=True)
            (root / 'src/tools/die_safety/ir_step.sh').write_text(
                f'echo DIE_IR_DROP {"PASS" if step_exit == 0 else "FAIL"}\nexit {step_exit}\n')
            if odb:
                (root / 'grt/grt.odb').write_text('test ODB identity')
            env = dict(os.environ, D=tmp, G=str(root / 'grt'), W=str(root / 'grt'),
                       SRC=str(root / 'src'), V='test')
            result = subprocess.run(['bash', '-c', 'say() { echo "$*"; };\n' + stage + '\nexit "$IR_RC"'],
                                    env=env, capture_output=True, text=True)
            return result

    def test_missing_odb_is_not_run_failure(self):
        r = self.stage()
        self.assertEqual(r.returncode, 1)
        self.assertIn('OWNER_REPORT die IR-drop NOT_RUN', r.stdout)

    def test_actual_odb_solver_pass(self):
        r = self.stage(odb=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('DIE_IR_DROP PASS', r.stdout)

    def test_actual_odb_solver_failure(self):
        r = self.stage(odb=True, step_exit=1)
        self.assertEqual(r.returncode, 1)
        self.assertIn('DIE_IR_DROP FAIL', r.stdout)


if __name__ == '__main__':
    unittest.main()
