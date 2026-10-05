"""Fail-closed runtime admission and source-list checks; no full-die builds."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('w17_rt', Path(__file__).with_name('v41_die_rt.py'))
R = importlib.util.module_from_spec(spec)
spec.loader.exec_module(R)


class RuntimeIntegration(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.img = self.root / 'images'
        self.work = self.root / 'work'
        self.work.mkdir()
        (self.work / 'v41_die_rt').write_text('fixture binary identity')
        for rank in range(4):
            d = self.img / f'r{rank}'
            d.mkdir(parents=True)
            (d / 'expect_vm.hex').write_text('00000000\n3f800000\n')

    def invoke(self, words='00000000\n3f800000\n', rc=0, fault='00', ranks=4):
        out = self.root / 'out'
        def fake_run(*args, **kwargs):
            for rank in range(4):
                (out / f'vm{rank}.hex').write_text(words)
            lines = [f'DONE die={r} cyc=10 core_cycles=10 fault={fault}' for r in range(ranks)]
            lines += ['END cycles=10' if rc == 0 else 'TIMEOUT cycles=10']
            return subprocess.CompletedProcess([], rc, '\n'.join(lines), '')
        argv = ['rt', 'run', '--work', str(self.work), '--images', str(self.img), '--out', str(out)]
        with patch.object(sys, 'argv', argv), patch.object(R.subprocess, 'run', fake_run):
            status = R.main()
        return status, json.loads((out / 'result.json').read_text())

    def test_exact(self):
        status, rec = self.invoke()
        self.assertEqual(status, 0)
        self.assertTrue(rec['pass_exact'])
        self.assertEqual(rec['source_sha256']['tools/v41_die_rt.py'], R.sha(Path(R.__file__)))

    def test_truncated_vm(self):
        status, rec = self.invoke(words='00000000\n')
        self.assertEqual(status, 1)
        self.assertFalse(rec['check']['r0']['length_ok'])

    def test_extra_vm(self):
        self.assertEqual(self.invoke(words='00000000\n3f800000\n00000000\n')[0], 1)

    def test_mismatch(self):
        self.assertEqual(self.invoke(words='00000000\n3f800001\n')[0], 1)

    def test_fault(self):
        self.assertEqual(self.invoke(fault='01')[0], 1)

    def test_missing_done(self):
        self.assertEqual(self.invoke(ranks=3)[0], 1)

    def test_timeout(self):
        status, rec = self.invoke(rc=1, ranks=0)
        self.assertEqual(status, 1)
        self.assertIsNone(rec['check'])

    def test_existing_result_preserved(self):
        self.invoke(rc=1, ranks=0)
        old = (self.root / 'out/result.json').read_bytes()
        with self.assertRaises(SystemExit):
            self.invoke()
        self.assertEqual((self.root / 'out/result.json').read_bytes(), old)

    def test_source_lists(self):
        for l20 in (False, True):
            src = R.all_sources(l20)
            self.assertFalse([str(p) for p in src if not p.is_file()])
            names = {p.name for p in src}
            self.assertIn('ot_w15_coll_dma.sv', names)
            self.assertIn('ot_w15_rom_oneshot_px.sv', names)
            self.assertIn('ot_coll_topk_merge.sv', names)
            self.assertIn('ot_hdc_fp32_add_lat.sv', names)
            self.assertIn('ot_hdc_fastfp_lat.sv', names)
            self.assertIn('ot_hdc_isa_v41_profiles.svh', names)
        self.assertIn(R.ROOT / 'tools/w11_ckvdie_src_l20.txt', R.all_sources(True))
        self.assertIn(R.ROOT / 'tools/w17_runtime_rtl_chip_v41x_die_smoke.py', R.all_sources(False))


if __name__ == '__main__':
    unittest.main()
