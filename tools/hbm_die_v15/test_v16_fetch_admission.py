import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from v16_fetch import REMOTE_PY, check_sources


class FetchAdmission(unittest.TestCase):
    def test_ignored_wrapper_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); d = root / 'syn' / 'cell'; d.mkdir(parents=True)
            (d / 'cell.ys').write_text('hierarchy -check -top default_master\n')
            r = subprocess.run([sys.executable, '-c', REMOTE_PY, tmp, tmp, 'cell', 'parameter_wrapper'],
                               capture_output=True, text=True)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn('Wrong synthesized top', r.stderr)

    def test_actual_source_and_wrapper_hashes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); d = root / 'syn' / 'cell'; d.mkdir(parents=True)
            src = root / 'src'; (src / 'v16w').mkdir(parents=True)
            wrapper = b'module parameter_wrapper; endmodule\n'
            (src / 'v16w' / 'wrapper.sv').write_bytes(wrapper)
            (d / 'cell.ys').write_text('read_verilog -sv v16w/wrapper.sv\nhierarchy -check -top parameter_wrapper\n')
            (d / 'cell.stat').write_text("Chip area for top module 'parameter_wrapper': 12.5\n")
            (d / 'cell.files.json').write_text(json.dumps({'macros': []}))
            r = subprocess.run([sys.executable, '-c', REMOTE_PY, tmp, str(src), 'cell', 'parameter_wrapper'],
                               capture_output=True, text=True, check=True)
            m = json.loads(r.stdout)
            self.assertEqual(m['actual_top'], 'parameter_wrapper')
            self.assertEqual(m['source_file_sha256']['v16w/wrapper.sv'], hashlib.sha256(wrapper).hexdigest())
            (root / 'views' / 'wrap').mkdir(parents=True)
            (root / 'views' / 'wrap' / 'wrapper.sv').write_bytes(wrapper)
            check_sources(m, 'HEAD', root / 'views')
            (root / 'views' / 'wrap' / 'wrapper.sv').write_bytes(wrapper + b'// different parameters\n')
            with self.assertRaisesRegex(ValueError, 'Parameter wrapper mismatch'):
                check_sources(m, 'HEAD', root / 'views')

    def test_modified_snapshot_source_is_rejected(self):
        path = 'tools/hbm_die_v15/synth_master.sh'
        with self.assertRaisesRegex(ValueError, 'Source differs'):
            check_sources({'source_file_sha256': {path: '0' * 64}}, 'HEAD', '.')


if __name__ == '__main__':
    unittest.main()
