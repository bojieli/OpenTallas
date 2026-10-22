import unittest
from ks_descriptor import encode, decode, validate, fixture_word


class KSDescriptorTest(unittest.TestCase):
    fields = dict(user=0, token=16754, position=1048575)

    def test_fixture_roundtrip_matches_rtl_wire_fields(self):
        word = encode(**self.fields)
        self.assertEqual(word, 0x1000082e4fffff)
        self.assertEqual(decode(word), self.fields)
        self.assertEqual(encode(**decode(word)), word)

    def test_inherited_swapped_word_is_not_fixture_descriptor(self):
        old = 0x1001ffffe04172
        self.assertEqual(decode(old), dict(user=0, token=1048575, position=16754))
        with self.assertRaises(ValueError):
            validate(old, **self.fields)

    def test_independent_wrong_token_position_and_user_rejected(self):
        for field in self.fields:
            changed = dict(self.fields); changed[field] += 1
            with self.assertRaises(ValueError):
                fixture_word(self.fields, user=0, supplied=encode(**changed))

    def test_wire_width_and_inactive_descriptor_rejected(self):
        for field, width in [('user', 10), ('token', 21), ('position', 21)]:
            changed = dict(self.fields); changed[field] = 1 << width
            with self.assertRaises(ValueError):
                encode(**changed)
        with self.assertRaises(ValueError):
            decode(encode(**self.fields) & ((1 << 52)-1))


if __name__ == '__main__':
    unittest.main()
