import hashlib
import importlib.util
import py_compile
import tempfile
import unittest
from pathlib import Path
P=Path(__file__).resolve().parents[1]/'tools/dsrom_native_masked_r2_verify.py'
s=importlib.util.spec_from_file_location('r2verify',P)
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)

class CacheProjection(unittest.TestCase):
    def test_source_only_poisoned_valid_cache(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'codec.py';p.write_text("raise RuntimeError('POISONED_CACHE_READ')\n")
            py_compile.compile(str(p),doraise=True)
            old=p.stat();p.write_text('value = 123\n')
            # Any cached bytecode must be irrelevant, whether stale or valid.
            self.assertEqual(m.source_module(p).value,123)
    def test_cache_only_projection(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'a.py';p.write_text('x=1\n')
            h=hashlib.sha256(p.read_bytes()).hexdigest()
            x=m.verify_receipt(t,{'a.py':h,'inputs/__pycache__/a.cpython-310.pyc':'absent-old-cache'})
            self.assertEqual(x['checked'],['a.py']);self.assertEqual(len(x['excluded_caches']),1)
            p.write_text('x=2\n')
            with self.assertRaises(ValueError):m.verify_receipt(t,{'a.py':h})
    def test_noncache_pyc_missing_is_not_excluded(self):
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaises(FileNotFoundError):m.verify_receipt(t,{'actual.pyc':'bad'})
    def test_not_all_files_under_cache_are_disposable(self):
        self.assertFalse(m.cache_path('inputs/__pycache__/real.sv'))
        self.assertFalse(m.cache_path('inputs/notcache/real.pyc'))
    def test_source_manifest_no_cache(self):
        x=m.verify();self.assertFalse(x['excluded_caches'])
    def test_frozen_gate_is_reset_gated(self):
        p=m.ROOT/'rtl/model_ready_ds_native_vm_r2_20261003/ot_v41_vm_bank4_macro_pipe_masked_visible_r2.sv'
        x=p.read_text()
        self.assertIn('assign wr_accept_v = {4{rst_n}} & wr_v & ~wr_bad;',x)
        self.assertIn('assign rd_accept_v = rst_n && rd_v && !(|rd_bad);',x)
        self.assertIn('wr_cmd_v_q <= wr_accept_v;',x)
        self.assertIn('rd_cmd_v_q <= {4{rd_accept_v}};',x)
if __name__=='__main__':unittest.main()
