"""Shared IDs/attribute controls; never evaluates floating arithmetic."""
import unittest
from tools.gpu_sys.canonical_qwen_native_opcode_abi import OPCODES,dispatch,movement_model

class NativeOpcodeABITests(unittest.TestCase):
    def test_preserve_boole_ids(self):
        self.assertEqual([OPCODES[n] for n in ('COPY','IADD','FCMP_GT','SELECT','FMIN')],[0,6,10,14,16])
        self.assertEqual(len(set(OPCODES.values())),40)
    def test_default_canonical_zero_only_source_operations(self):
        for op in ('FADD','FMUL','DIV','SQRT'):
            self.assertTrue(dispatch(op,{})['canonical_zero'])
            self.assertFalse(dispatch(op,{'canonical_zero':False})['canonical_zero'])
        for op in ('FMAX','FMIN','LDEXP','BITCAST_F'):
            self.assertFalse(dispatch(op,{})['canonical_zero'])
    def test_no_local_opcode_truncation_or_unowned_arithmetic(self):
        self.assertEqual(dispatch('FADD',{})['engine'],'fp32')
        self.assertEqual(dispatch('CONST',{})['engine'],'movement')
        self.assertEqual(dispatch('IMOD',{})['engine'],'UNBOUND_integer_multiply_modulo')
        with self.assertRaises(ValueError):dispatch('FADD',{'canonical_zero':1})
    def test_full_buffer_mux_cost_not_four_word_free_mux(self):
        m=movement_model()
        self.assertEqual(m['operand_retained_bus_bits'],24576)
        self.assertEqual(m['mux_2to1_64bit_equivalents'],98304)
        self.assertEqual(m['extra_state_bits'],0)
        self.assertFalse(m['headline_adopt'])

if __name__=='__main__':unittest.main()
