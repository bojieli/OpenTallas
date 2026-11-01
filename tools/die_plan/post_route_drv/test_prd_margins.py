import os
import pathlib
import subprocess
import tempfile
import unittest

HERE = pathlib.Path(__file__).parent

class Margins(unittest.TestCase):
    def test_explicit_settings_survive_shell_boundary(self):
        mk = (HERE / 'prd_mk.sh').read_text()
        block = mk[mk.index('for setting in OT_SLEW_MARGIN'):mk.index('[ ${V:0:1} = b ]')]
        for setup in ('30', ''):
            with self.subTest(setup=setup), tempfile.TemporaryDirectory() as d:
                env = dict(os.environ, OUT=d, OT_SLEW_MARGIN='40', OT_SETUP_MARGIN=setup,
                           OT_HOLD_ALLOW_SETUP='0', OT_HOLD_MAXBUF='17')
                script = 'printf "OT_SLEW_MARGIN=20\\nOT_SETUP_MARGIN=10\\n" > "$OUT/variant.env"\n' + block
                script += '\nsource "$OUT/variant.env"; printf "%s|%s|%s|%s" "$OT_SLEW_MARGIN" "$OT_SETUP_MARGIN" "$OT_HOLD_ALLOW_SETUP" "$OT_HOLD_MAXBUF"'
                p = subprocess.run(['bash', '-eu', '-c', script], env=env, capture_output=True, text=True)
                self.assertEqual(p.returncode, 0, p.stderr)
                self.assertEqual(p.stdout, f'40|{setup}|0|17')

    def test_unset_settings_keep_existing_defaults(self):
        mk = (HERE / 'prd_mk.sh').read_text()
        block = mk[mk.index('for setting in OT_SLEW_MARGIN'):mk.index('[ ${V:0:1} = b ]')]
        with tempfile.TemporaryDirectory() as d:
            env = {k: v for k, v in os.environ.items() if k not in ('OT_SLEW_MARGIN','OT_SETUP_MARGIN','OT_HOLD_ALLOW_SETUP','OT_HOLD_MAXBUF')}
            env['OUT'] = d
            p = subprocess.run(['bash', '-eu', '-c', 'echo OT_SLEW_MARGIN=20 > "$OUT/variant.env"\n'+block+'\ncat "$OUT/variant.env"'],env=env,capture_output=True,text=True)
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertEqual(p.stdout, 'OT_SLEW_MARGIN=20\n')
