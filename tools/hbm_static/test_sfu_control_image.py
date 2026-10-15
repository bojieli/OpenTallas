import re
import unittest
from pathlib import Path
from sfu_control_image import FIELDS, WIDTH, encode, pack, unpack

class ImageTest(unittest.TestCase):
    def test_abi_matches_rtl_declarations_and_concatenation(self):
        rtl = (Path(__file__).resolve().parents[2] / 'rtl/hbm_accel/generic/peers/ot_hgi_sfu_arithmetic_grid.sv').read_text()
        actual = re.search(r'assign \{([^}]+)\}=control;', rtl).group(1)
        names = [name.strip() for name in actual.split(',')]
        widths = dict((name, int(hi)+1) for hi, name in re.findall(r'wire \[(\d+):0\] (r_\w+);', rtl))
        self.assertEqual([(name.removeprefix('r_'), widths[name]) for name in names], list(FIELDS))
        fields = {name: ((1 << width)-1) ^ ((1 << (width-1))-1) for name, width in FIELDS}
        self.assertEqual(unpack(pack(fields)), fields)
        self.assertEqual(pack({}), 0)
        self.assertEqual(WIDTH, 1742)

    def test_calendar_and_failure_boundaries(self):
        words = encode(dict(cycles=3, rows=[dict(cycle=1, fields=dict(emit=1, i_v=7167))]))
        self.assertEqual(words[0], 0)
        self.assertEqual(unpack(words[1])['i_v'], 7167)
        for name, width in FIELDS:
            for bad in (-1, 1 << width):
                with self.assertRaises(ValueError): pack({name: bad})
        for rows in ([dict(cycle=3,fields={})], [dict(cycle=1,fields={})]*2):
            with self.assertRaises(ValueError): encode(dict(cycles=3,rows=rows))
        with self.assertRaises(ValueError): pack(dict(ready=1))

if __name__ == '__main__': unittest.main()
