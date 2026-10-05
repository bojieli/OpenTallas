import struct,tempfile,unittest
from pathlib import Path
from h4_c0_ds_external_source_archive import ownership,npy_header

class ExternalRolesTests(unittest.TestCase):
    def test_expected_intermediate_is_never_initializer(self):
        for row in [{'scope':'independent expected numerical output'}, {'runtime_operand_source':False}, {'golden_stimuli_in_executor':True}]:
            self.assertEqual(ownership('selected_codes',row)[0],'COMPARISON_ONLY_FORBIDDEN_AS_DUT_INPUT')
    def test_descriptor_still_requires_actual_route_selection(self):
        role,gate=ownership('expert_descriptor_table',{'scope':'released checkpoint source initializer'})
        self.assertEqual(role,'INITIAL_IMMUTABLE_DESCRIPTOR');self.assertIn('Actual route IDs/version',gate)
        self.assertIn('not physical HBM',gate)
    def test_prefetched_rows_do_not_qualify_actual_request(self):
        role,gate=ownership('selected_row_ids',{'scope':'released checkpoint row response'})
        self.assertEqual(role,'INITIAL_IMMUTABLE_ROW_RESPONSE_CANDIDATE');self.assertIn('actual computed row IDs',gate)
    def test_entering_state_is_not_future_producer_state(self):
        role,gate=ownership('open_group',{'scope':'exact source entering old open group'})
        self.assertEqual(role,'INITIAL_IMMUTABLE_ENTERING_STATE');self.assertIn('actual producer',gate)
    def test_unknown_operand_refuses_source_guess(self):
        self.assertEqual(ownership('unknown',{'scope':'source'})[0],'UNCLASSIFIED_SOURCE_REFUSAL')
    def test_header_only_parser_cannot_execute_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'data.npy';header=b"{'descr': '<f4', 'fortran_order': False, 'shape': (1, 2), }\n"
            p.write_bytes(b'\x93NUMPY\x01\x00'+struct.pack('<H',len(header))+header+b'\x00'*8)
            got,offset=npy_header(p);self.assertEqual(got['shape'],(1,2));self.assertEqual(offset,len(header)+10)
            dangerous=b"__import__('os').system('false')\n"
            p.write_bytes(b'\x93NUMPY\x01\x00'+struct.pack('<H',len(dangerous))+dangerous)
            with self.assertRaises(ValueError):npy_header(p)

if __name__=='__main__':unittest.main()
