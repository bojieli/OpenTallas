import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('launch_inputs', ROOT/'tools/qwen_rom_combined_launch.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class LaunchInputTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.embedding = self.root/'embedding.bin'
        self.embedding.write_bytes((6280).to_bytes(4, 'little') + b'\x80\x3f' + bytes(range(256))*16)

    def test_actual_embedding_abi_preserves_high_code_bytes(self):
        self.assertEqual(m.embedding_argument(self.embedding, m.sha(self.embedding), 6280),
                         ['--embed-bin', str(self.embedding.resolve())])
        self.assertEqual(self.embedding.read_bytes()[-1], 255)

    def test_wrong_token_hash_and_extent_refuse(self):
        with self.assertRaisesRegex(ValueError, 'token differs'):
            m.embedding_argument(self.embedding, m.sha(self.embedding), 0)
        with self.assertRaisesRegex(ValueError, 'identity'):
            m.embedding_argument(self.embedding, '0'*64, 6280)
        self.embedding.write_bytes(self.embedding.read_bytes()[:-1])
        with self.assertRaisesRegex(ValueError, 'extent'):
            m.embedding_argument(self.embedding, m.sha(self.embedding), 6280)

    def test_prepare_only_cli_enrolls_embedding_without_runtime(self):
        baseline = self.root/'baseline.json'
        baseline.write_text(json.dumps({'token':6280}))
        output = self.root/'output'
        output.mkdir()
        record = {'token':6280, 'input_sha256':{}}
        args = []
        for name in ('selection', 'stages', 'preload', 'oracle-root'):
            args += ['--'+name, str(self.root/name)]
        args += ['--baseline',str(baseline),'--output',str(output),
                 '--embedding-bin',str(self.embedding),'--embedding-sha256',m.sha(self.embedding),'--prepare-only']
        with patch.object(m, 'prepare', return_value=(['actual-binary'],record)), \
             patch.object(m.subprocess, 'Popen', side_effect=AssertionError('must not launch')):
            self.assertEqual(m.main(args), 0)
        launch=json.loads((output/'launch.json').read_text())
        self.assertEqual(launch['command'], ['actual-binary','--embed-bin',str(self.embedding)])
        self.assertEqual(launch['input_sha256'][str(self.embedding)],m.sha(self.embedding))


if __name__ == '__main__':unittest.main()
