import copy
import hashlib
import json
import struct
import tempfile
import unittest
from pathlib import Path
import dv_lower as D
import dv_lower_vec as V
import head_norm_object as H


def ownership():
    return dict(slice_rtl='s8', residual=dict(blocks_per_slice=[list(range(s,32,12)) for s in range(12)]))


class HeadNormObjectTest(unittest.TestCase):
    def test_all4096_gain_words_follow_actual_native_ownership(self):
        words=[0x3f000000+i for i in range(4096)]
        obj=H.build(words,ownership());seen={}
        self.assertFalse(obj['executable']);self.assertEqual(obj['gain_payloads'],256)
        for sl in obj['slices']:
            for rec in sl['gain_payloads']:
                payload=int(rec['payload_hex'],16)
                for lane,g in enumerate(rec['global_elements']):
                    self.assertNotIn(g,seen)
                    self.assertEqual((payload>>(64*lane))&((1<<64)-1),words[g]);seen[g]=1
        self.assertEqual(set(seen),set(range(4096)))

    def test_native_multiply_order_and_symbolic_crom(self):
        obj=H.build([0]*4096,ownership())
        for sl in obj['slices']:
            w=int(sl['apply_su_template_hex'],16);f=D.su_unpack(w)
            self.assertLess(w,1<<457);self.assertEqual(f['ma'],V.MA_AB)
            self.assertEqual((f['mc'],f['md'],f['ad'],f['sfu'],f['red']),(1,0,0,0,0))
            self.assertEqual((f['a'],f['b'],f['csrc'],f['c']),(0,400,1,0))
            self.assertEqual((f['nin'],f['nout']),(128,len(sl['blocks'])))
            self.assertEqual(f['d'],D.W_X|128*sl['blocks'][0])
            self.assertIsNone(sl['prog_slot'])
            reloc=sl['relocations'][0]
            self.assertEqual((w>>reloc['bit'])&((1<<reloc['width'])-1),0)
            self.assertEqual(D.su_unpack(w|(1472<<reloc['bit']))['c'],1472)

    def test_reject_ownership_alias_and_wrong_source_shape(self):
        bad=ownership();bad['residual']['blocks_per_slice'][0][0]=1
        with self.assertRaisesRegex(ValueError,'cover32'):H.build([0]*4096,bad)
        with self.assertRaisesRegex(ValueError,'4096'):H.build([0]*4095,ownership())

    def test_recovered_tensor_identity_and_mutant(self):
        vals=[0x3f80+i%7 for i in range(4096)]
        meta=dict(norm_source=dict(dtype='BF16',source_tensor_sha256=hashlib.sha256(struct.pack('<4096H',*vals)).hexdigest()))
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'gain.hex';p.write_text(''.join(f'{v<<16:016x}\n' for v in vals))
            self.assertEqual(H.gains(p,meta),[v<<16 for v in vals])
            lines=p.read_text().splitlines();lines[212]=f'{(vals[212]^1)<<16:016x}';p.write_text('\n'.join(lines)+'\n')
            with self.assertRaisesRegex(ValueError,'checkpoint tensor'):H.gains(p,meta)

if __name__=='__main__':unittest.main()
