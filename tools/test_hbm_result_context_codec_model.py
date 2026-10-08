import random
import unittest
from hbm_result_context_codec_model import context_codec_model
from hbm_result_relay_protection_model import crc32c

class ContextCodecTests(unittest.TestCase):
    def test_matrix_and_cost(self):
        model = context_codec_model()
        masks = [int(v,16) for v in model['matrix_masks_hex']]
        rng = random.Random(380)
        for _ in range(100):
            message = rng.getrandbits(380)
            self.assertEqual(crc32c(message,380),sum(((message&m).bit_count()&1)<<i for i,m in enumerate(masks)))
        self.assertEqual(model['encoder_FF_bits'],1654)
        self.assertEqual(model['duplicated_checker_FF_bits'],4304)
        self.assertEqual(model['total_codec_cycles_per_result'],11)

    def test_wrong_source_same_beat_and_payload(self):
        for record in (0,1,65535):
            for owner in (0,1,(1<<73)-1):
                checks = [crc32c(1 | (7<<270) | (source<<286) | (record<<291) | (owner<<307),380) for source in range(32)]
                self.assertEqual(len(set(checks)),32)

    def test_context_and_checksum_single_double_fault_syndromes(self):
        columns = [crc32c(1<<i,380) for i in range(380)] + [1<<i for i in range(32)]
        self.assertTrue(all(columns))
        self.assertEqual(len(set(columns)),412)

    def test_zero_reset_not_nonzero_context_idle(self):
        self.assertEqual(crc32c(0,380),0)
        for context_bit in range(286,380):
            self.assertNotEqual(crc32c(1<<context_bit,380),0)

if __name__ == '__main__': unittest.main()
