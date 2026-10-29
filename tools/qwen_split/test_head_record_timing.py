from types import SimpleNamespace as NS
import unittest
from head_record_timing import derive


class RecordTiming(unittest.TestCase):
    def ctx(self, head=8, witness=8, data=5, valid=5):
        def timing(sink, port):
            if sink=='sys_face':
                source='d2d_rom'; stages=head if port=='prog_head_context_slot' else witness
            else:
                source='sys_face'; stages=valid if port=='prog_tx_observed_v' else data
            return {0:dict(kind='intra',source=source,source_port=port,landed_stages=stages)}
        return NS(timing_depths=timing)

    def test_shared_actual_capture18_includes_all_five_source_stages(self):
        result=derive(self.ctx())
        self.assertEqual(result['port1_txd'],18)
        self.assertEqual(result['send_slot_to_bank_sample_edges'],10)

    def test_current_unaligned_callback4_is_not_a_shared_capture_age(self):
        with self.assertRaisesRegex(ValueError,'HEAD 8, witness 4'):
            derive(self.ctx(witness=4))

    def test_valid_payload_off_by_one_is_not_coherent(self):
        with self.assertRaisesRegex(ValueError,'incoherent'):
            derive(self.ctx(valid=4))


if __name__=='__main__':
    unittest.main()
