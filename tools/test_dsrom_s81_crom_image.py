import unittest
from dsrom_s81_crom_image import parse_crom, qualify_gamma


class CromImage(unittest.TestCase):
    def test_lane_order_and_raw_BF16_exception_bits(self):
        raw=b''.join(v.to_bytes(2,'little') for v in (0x8000,0x7fc1,0x0001))
        words={i:(0x12345678<<32)|(v<<16) for i,v in enumerate((0x8000,0x7fc1,0x0001))}
        self.assertEqual(qualify_gamma(words,raw,'BF16',[(1,i) for i in range(3)]),3)
        parsed=parse_crom(b'@0\n1234567880000000\n')
        self.assertEqual(parsed[0]&0xffffffff,0x80000000)
        self.assertEqual(parsed[0]>>32,0x12345678)

    def test_corrupted_or_missing_gamma_refused(self):
        for words in ({0:0x3f800001},{}):
            with self.subTest(words=words),self.assertRaisesRegex(ValueError,'rawbits mismatch'):
                qualify_gamma(words,b'\x80\x3f','BF16',[(1,0)])

    def test_source2_wrong_address_or_duplicate_coverage_refused(self):
        for addresses in ([(2,0)],[(1,1)],[(1,0),(1,0)]):
            with self.subTest(addresses=addresses),self.assertRaisesRegex(ValueError,'coverage'):
                qualify_gamma({0:0},b'\0\0','BF16',addresses)

    def test_duplicate_width_and_bounds_refused(self):
        for raw in (b'@0\n0\n@0\n0\n',b'@80000\n0\n',b'@0\n10000000000000000\n'):
            with self.subTest(raw=raw),self.assertRaises(ValueError):parse_crom(raw)

    def test_F32_bits_and_unsupported_dtype(self):
        self.assertEqual(qualify_gamma({0:0x80000000},b'\0\0\0\x80','F32',[(1,0)]),1)
        with self.assertRaisesRegex(ValueError,'dtype'):
            qualify_gamma({0:0},b'\0\0','F16',[(1,0)])


if __name__=='__main__':unittest.main()
