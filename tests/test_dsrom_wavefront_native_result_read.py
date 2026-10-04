"""Native output wiring preservation; no controller qualification or model build."""
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('read',ROOT/'tools/dsrom_wavefront_native_result_read.py')
W=importlib.util.module_from_spec(spec);spec.loader.exec_module(W)


class NativeResultPorts(unittest.TestCase):
    def test_actual_core_outputs_and_original_top_body(self):
        p=ROOT/'rtl/dsrom_sys/wavefront_result_origin_parent/native'/W.TOP
        original=p.read_text();adapted=W.transform(original)
        recovered=adapted.replace('    parameter integer NATIVE_RESULT_READ=0,\n','').replace(W.PORTS,'')
        recovered=recovered.replace('.core_next_token(native_result_token), .core_next_val(native_result_value)', '.core_next_token(), .core_next_val()').replace(W.EXPORTS,'')
        self.assertEqual(recovered,original)
        self.assertIn('.host_mode(1\'b1)',adapted)
        self.assertIn('dut.u_tile.u_core.e_ready[dut.u_tile.u_core.EAM]',adapted)
        self.assertIn('dut.u_tile.u_core.me_amax',adapted)
        selected=dict(sources=[p],source_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest()},parameters={'PKG_WAVE':0})
        with tempfile.TemporaryDirectory() as out:
            r=W.install(selected,out)
            self.assertEqual(r['parameters']['NATIVE_RESULT_READ'],0)
            self.assertFalse(r['native_terminal_producer_bound'])
            self.assertEqual(r['source_sha256'],W.install(selected,out,enable=True)['source_sha256'])
            self.assertEqual(original,p.read_text())
            r['sources'][0].write_text('changed')
            with self.assertRaises(FileExistsError):W.install(selected,out)

    def test_wrong_pin_hook_and_source_output_refused(self):
        p=ROOT/'rtl/dsrom_sys/wavefront_result_origin_parent/native'/W.TOP
        selected=dict(sources=[p],source_sha256={str(p):'wrong'})
        with tempfile.TemporaryDirectory() as out:
            with self.assertRaises(ValueError):W.install(selected,out)
            self.assertEqual(list(Path(out).iterdir()),[])
        with self.assertRaises(ValueError):W.transform('no selected native top')
        with self.assertRaises(ValueError):W.install(selected,p.parent)


if __name__=='__main__':unittest.main(verbosity=2)
