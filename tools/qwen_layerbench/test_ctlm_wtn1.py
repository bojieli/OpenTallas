"""F16 WTN1 template splice into the tt_ctlm deployment image (ctlm_image.py --wtn1)."""
import copy, json, unittest
from pathlib import Path
import ctlm_image as C

MAN = Path(C.ROOT) / 'results/arch/qwen_calendar_integration_1019/witness/witness_template_packet/manifest.json'


class Wtn1Splice(unittest.TestCase):
    def setUp(self):
        self.m = json.loads(MAN.read_text())
        self.img = [0] * (C.PW + C.DW)
        self.img[0] = 0x1234; self.img[399] = 7; self.img[439] = 9; self.img[1023] = 0xf00

    def test_splice_exact(self):
        out, rec = C.splice_wtn1(self.img, self.m)
        for i, r in enumerate(self.m['records']):
            self.assertEqual(out[400 + 3 * i:403 + 3 * i], [int(w, 16) for w in r['words']])
        # everything outside PW400..438 unchanged; record0 header in place
        self.assertEqual([out[i] for i in range(len(out)) if not 400 <= i <= 438],
                         [self.img[i] for i in range(len(out)) if not 400 <= i <= 438])
        self.assertEqual(out[402] >> 6, C.WTN1_HEADER >> 6)
        self.assertEqual(rec['added_PW_transfers'], 0)
        self.assertNotEqual(C.digest(out), C.digest(self.img))

    def test_refuse_collision(self):
        self.img[417] = 1
        with self.assertRaises(C.CompileError):
            C.splice_wtn1(self.img, self.m)

    def test_refuse_reordered_or_bad_header(self):
        m = copy.deepcopy(self.m); m['records'][3], m['records'][4] = m['records'][4], m['records'][3]
        with self.assertRaises(C.CompileError):
            C.splice_wtn1(self.img, m)
        m = copy.deepcopy(self.m); w = int(m['records'][0]['words'][2], 16) ^ (1 << 40)
        m['records'][0]['words'][2] = f'{w:016x}'
        with self.assertRaises(C.CompileError):
            C.splice_wtn1(self.img, m)
        m = copy.deepcopy(self.m); m['records'] = m['records'][:12]
        with self.assertRaises(C.CompileError):
            C.splice_wtn1(self.img, m)


if __name__ == '__main__':
    unittest.main()
