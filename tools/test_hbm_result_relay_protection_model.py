"""Analytical codeword tests, not implementation or consumer fault qualification."""
import random
import unittest
from hbm_result_relay_protection_model import crc32c, protection_options

MASK = (1 << 286) - 1

def encode(payload, sequence):
    message = payload | (sequence << 270)
    return message | (crc32c(message) << 286)

def accepts(frame, expected):
    message = frame & MASK
    return crc32c(message) == (frame >> 286) and (message >> 270) == expected

class ProtectionModelTests(unittest.TestCase):
    def test_all_single_and_double_bit_syndromes(self):
        columns = [crc32c(1 << i) for i in range(286)] + [1 << i for i in range(32)]
        self.assertTrue(all(columns))
        for i, left in enumerate(columns):
            for right in columns[i+1:]:
                self.assertNotEqual(left ^ right, 0)

    def test_idle_valid_fault_row_data_and_checksum_corruption(self):
        rng = random.Random(20261007)
        for sequence in (0, 1, 65535):
            for payload in (0, 1, rng.getrandbits(270)):
                frame = encode(payload, sequence)
                self.assertTrue(accepts(frame, sequence))
                # Every bit is checked even when rv is zero, including metadata.
                for bit in range(318):
                    self.assertFalse(accepts(frame ^ (1 << bit), sequence))
        self.assertEqual(encode(0, 0), 0)

    def test_sequence_replay_and_wrap(self):
        self.assertFalse(accepts(encode(1, 65535), 0))
        self.assertTrue(accepts(encode(1, 0), 0))
        self.assertFalse(accepts(encode(1, 0), 1))

    def test_matrix_and_full_alignment_cost(self):
        model = protection_options()['crc_candidate']
        masks = [int(mask, 16) for mask in model['matrix_masks_hex']]
        rng = random.Random(318)
        for _ in range(128):
            value = rng.getrandbits(286)
            matrix_crc = sum(((value & mask).bit_count() & 1) << bit for bit, mask in enumerate(masks))
            self.assertEqual(matrix_crc, crc32c(value))
        self.assertEqual(model['duplicated_checker_FF_bits'], 3296)
        self.assertEqual(model['candidate_total_transport_cycles'], 79)
        self.assertEqual(model['frame_bits'], 318)

if __name__ == '__main__':
    unittest.main()
