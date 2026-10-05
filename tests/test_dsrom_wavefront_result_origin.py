"""Additive observational source/port checks only, no controller replay."""
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('result_origin',ROOT/'tools/dsrom_wavefront_result_origin.py')
W=importlib.util.module_from_spec(spec);spec.loader.exec_module(W)


def fixture():
    paths=[ROOT/'rtl/dsrom_sys/wavefront_parent/native'/n for n in W.ROLES]
    return dict(sources=paths,parameters={'PKG_WAVE':0},verilator_args=[],
                source_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})


class ResultPorts(unittest.TestCase):
    def test_body_and_state_byte_identical_except_observation_exports(self):
        selected=fixture();original=selected['sources'][2].read_text()
        adapted=W.controller(original)
        recovered=adapted.replace('module ot_rom_pkg_ctrl_wf_s81_origin #(','module ot_rom_pkg_ctrl_wf_s81 #(')
        recovered=recovered.replace('    output wire result_origin_valid,\n    output wire [USER_W-1:0] result_origin_user,\n    output wire [NW-1:0] result_origin_pos,\n    output wire result_origin_final,\n','')
        recovered=recovered.replace('\n    assign result_origin_valid = WAVE && SOURCE && res_v;\n    assign result_origin_user = res_u;\n    assign result_origin_pos = res_p;\n    assign result_origin_final = result_origin_valid && (red_n == RESULT_PARTS);\n','')
        self.assertEqual(recovered,original)
        self.assertNotIn('result_origin_user = cur_user',adapted)
        self.assertNotIn('result_origin_user = tok_user',adapted)
        with tempfile.TemporaryDirectory() as out:
            before=[p.read_bytes() for p in selected['sources']]
            r=W.install(selected,out)
            self.assertEqual(r['parameters'],selected['parameters'])
            self.assertFalse(r['result_origin_accepted_ledger_bound'])
            die,top=[p.read_text() for p in r['sources'][:2]]
            self.assertIn('.result_origin_user(wf_result_user)',die)
            self.assertIn('.wf_result_user(wf_result_user)',top)
            self.assertEqual(before,[p.read_bytes() for p in selected['sources']])
            self.assertEqual(r['source_sha256'],W.install(selected,out)['source_sha256'])

    def test_missing_pin_wrong_hook_and_immutable_output_fail_closed(self):
        selected=fixture()
        with tempfile.TemporaryDirectory() as out:
            selected['source_sha256'][str(selected['sources'][2])]='wrong'
            with self.assertRaises(ValueError):W.install(selected,out)
            self.assertFalse(list(Path(out).iterdir()))
            selected=fixture();r=W.install(selected,out)
            r['sources'][0].write_text('changed')
            with self.assertRaises(FileExistsError):W.install(selected,out)
        with self.assertRaises(ValueError):W.controller('not the actual controller')


if __name__=='__main__':unittest.main(verbosity=2)
