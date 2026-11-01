import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import native_stub_metadata as native
import lec

HEADER = '''(* blackbox *) module native_rom #(parameter integer RSTP=1, CGR=0, parameter INSTANCE="") (input clk, output q); endmodule
(* blackbox *) module native_bf #(parameter integer MB=0, parameter INSTANCE="") (input clk, output q); endmodule
'''


class NativeMetadataTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.k = Path(self.tmp.name)
        (self.k/'native_bb.v').write_text(HEADER)
        (self.k/'top.sv').write_text('selected canonical instance bindings')
        sha = lambda p: hashlib.sha256((self.k/p).read_bytes()).hexdigest()
        self.c = dict(schema=native.SCHEMA, top='top', headers={'native_bb.v': sha('native_bb.v')},
                      source_hashes={'top.sv': sha('top.sv')}, bindings={
                          'u_bound.e0': dict(master='native_rom', content_label='rank0.e0'),
                          'u_bound.e2': dict(master='native_rom', content_label='rank0.e2'),
                          'u_bound.bf': dict(master='native_bf', content_label='')})
        self.data = {'modules': {'top': {'cells': {'u_bound': {'type':'bound'}}},
                      'bound': {'cells': {
                          'e0': {'type':'native_rom', 'parameters': {'INSTANCE':'rank0.e0', 'RSTP':'1'}},
                          'e2': {'type':'native_rom', 'parameters': {'INSTANCE':'rank0.e2', 'CGR':'0'}},
                          'bf': {'type':'native_bf', 'parameters': {'INSTANCE':' ', 'MB':'0'}}}},
                      'native_rom': {'attributes': {'blackbox':1}},
                      'native_bf': {'attributes': {'blackbox':1}}}}
        (self.k/native.CONTRACT).write_text(json.dumps(self.c))
        self.c, self.hp = native.load(self.k)

    def test_typed_stubs_preserve_labels_and_validate_all_bindings(self):
        before = copy.deepcopy(self.data)
        params, receipt = native.validate(self.data, self.c, self.hp)
        s = lec.stub_verilog({'native_rom':[('clk','input',1,0),('q','output',1,0)]}, params)
        self.assertIn('parameter INSTANCE = "";', s)
        self.assertIn('parameter integer RSTP = 1;', s)
        self.assertEqual(receipt['bindings']['u_bound.e0']['content_label'], 'rank0.e0')
        self.assertEqual(self.data, before)

    def test_wrong_instance_rejected(self):
        self.data['modules']['bound']['cells']['e0']['parameters']['INSTANCE']='rank1.e0'
        with self.assertRaisesRegex(ValueError, 'wrong native INSTANCE'): native.validate(self.data,self.c,self.hp)

    def test_unsupported_parameter_rejected(self):
        self.data['modules']['bound']['cells']['e0']['parameters']['IGNORE_ME']='0'
        with self.assertRaisesRegex(ValueError, 'unsupported native parameter'): native.validate(self.data,self.c,self.hp)

    def test_functional_parameter_mismatch_rejected(self):
        self.data['modules']['bound']['cells']['e0']['parameters']['RSTP']='0'
        with self.assertRaisesRegex(ValueError, 'differs from selected header'): native.validate(self.data,self.c,self.hp)

    def test_unlisted_instance_rejected(self):
        self.data['modules']['bound']['cells']['extra']=copy.deepcopy(self.data['modules']['bound']['cells']['e0'])
        with self.assertRaisesRegex(ValueError, 'unexpected native binding'): native.validate(self.data,self.c,self.hp)

    def test_missing_instance_rejected(self):
        del self.data['modules']['bound']['cells']['e2']
        with self.assertRaisesRegex(ValueError, 'missing selected native'): native.validate(self.data,self.c,self.hp)

    def test_changed_header_rejected(self):
        (self.k/'native_bb.v').write_text(HEADER.replace('RSTP=1','RSTP=0'))
        with self.assertRaisesRegex(ValueError, 'selected input changed'): native.load(self.k)

    def test_changed_source_rejected(self):
        (self.k/'top.sv').write_text('changed binding')
        with self.assertRaisesRegex(ValueError, 'selected input changed'): native.load(self.k)

    def test_optional_hook_does_not_change_unconfigured_kits(self):
        env={'DESIGN_NAME':'top', 'VERILOG_FILES':'top.sv'}
        (self.k/native.CONTRACT).unlink()
        self.assertNotIn('lec_native_before',lec.bb_script(env,self.k,'verilog',[],self.k/'bb'))

if __name__=='__main__':unittest.main()
