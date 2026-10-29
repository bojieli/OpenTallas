import unittest
from hbm_b2 import p3_issue_contract as P


class ContractTest(unittest.TestCase):
    def test_original_fragment_roundtrip_and_selector_lanes(self):
        fragments = [int.from_bytes(bytes((i + lane) % 256 for i in range(3152)), 'little') for lane in range(3)]
        packet = P.compile_load(fragments, fmt=2, enabled=True, first_edge=7, address=19)
        self.assertEqual(len(packet['events']), 42)
        for lane in range(3):
            events = packet['events'][lane * 14:(lane + 1) * 14]
            select = events[0]['beat_left'] & ((1 << 2069) - 1)
            self.assertEqual((select >> 2048) & 8191, 0)
            self.assertEqual(select & 7, 1 << lane)
            self.assertEqual((select >> 8) & 7, 7)
            restored = 0
            for g, event in enumerate(events[1:]):
                beat = event['beat_left'] & ((1 << 2069) - 1)
                self.assertEqual((beat >> 2048) & 8191, 1 << g)
                self.assertEqual((beat >> 2061) & 127, 19)
                restored |= (beat & ((1 << 2048) - 1)) << (2048 * g)
                self.assertEqual(event['beat_left'], event['beat_right'])
            self.assertEqual(restored, fragments[lane])
        self.assertIsNone(packet['dates']['first_safe_row'])
        self.assertFalse(packet['qualified'])

    def test_all_xs_straps_match_source_bit_offsets(self):
        config = P.xs_word()
        for c in range(8):
            for pair in range(2):
                for south in range(2):
                    word = config >> (52 * (2 * c + pair) + 26 * south)
                    row = 2 * pair + south
                    self.assertEqual(((word >> 9) & 31) * 2048 + (word & 511) * 4, c * 3152 + row * 532)
                    self.assertEqual(((word >> 21) & 31) * 2048 + ((word >> 14) & 127) * 16,
                                     c * 3152 + 2128 + row * 256)

    def test_refuses_unsupported_or_implicit_adoption(self):
        for kw in ({}, {'enabled': True, 'fmt': 3}, {'enabled': True, 'unit': 'ATT.QK'}):
            args = dict(fmt=0); args.update(kw)
            with self.assertRaises(ValueError):
                P.compile_load([0], **args)
        with self.assertRaises(ValueError): P.selector(4, 3)
        with self.assertRaises(ValueError): P.activation_beat(0, 13, 0)
        with self.assertRaises(ValueError): P.rows(1 << 818, 0)


if __name__ == '__main__': unittest.main()
