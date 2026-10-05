"""Independent raw-leaf mapping checks for the fixed full AR tile."""
import importlib.util
from pathlib import Path
import random
import unittest
P=Path(__file__).resolve().parents[1]/'tools/hbrom_protection_model.py'
S=importlib.util.spec_from_file_location('hbrom_protection_model',P)
M=importlib.util.module_from_spec(S);S.loader.exec_module(M)
def bits(cw):
    return [(r['leaf_start']+i,r['ingress_start']+i) for r in cw['runs'] for i in range(r['length'])]
def raw_global(sp,b):
    # Independent concatenated quant-bank and BF16-subfield representation.
    return sp*532+b if b<532 else 2128+sp*256+b-532
class ProtectionMapping(unittest.TestCase):
    def setUp(self):self.d=M.build()
    def test_every_raw_bit_once_and_exact_ingress(self):
        for leaf in self.d['activation_layout']:
            seen=[]
            for cw in leaf['codewords']:
                self.assertEqual(len(bits(cw))+cw['zero_pad'],64)
                for b,i in bits(cw):
                    self.assertEqual(2048*cw['beat']+i,raw_global(leaf['leaf'],b));seen.append(b)
            self.assertEqual(sorted(seen),list(range(788)))
    def test_codeword_masks_are_atomic_disjoint_and_fit_four_macros(self):
        for leaf in self.d['activation_layout']:
            used=set();bybeat=[set(),set()]
            for cw in leaf['codewords']:
                mask=set(range(cw['code_offset'],cw['code_offset']+72))
                self.assertFalse(used&mask);used|=mask;bybeat[cw['beat']]|=mask
            self.assertFalse(bybeat[0]&bybeat[1]);self.assertEqual(used,set(range(leaf['encoded_bits'])))
            self.assertLessEqual(leaf['encoded_bits'],1024)
            # Codewords crossing a 256-bit macro boundary retain one ingress owner.
            self.assertTrue(any(c['code_offset']//256 != (c['code_offset']+71)//256 for c in leaf['codewords']))
    def test_leaf_three_split(self):
        l=self.d['activation_layout'][3]
        self.assertEqual([sum(len(bits(c)) for c in l['codewords'] if c['beat']==b) for b in [0,1]],[452,336])
        self.assertEqual([sum(c['beat']==b for c in l['codewords']) for b in [0,1]],[8,6]);self.assertEqual(l['encoded_bits'],1008)
    def test_independent_repeated_and_reordered_partial_writes(self):
        rng=random.Random(7301)
        for leaf in self.d['activation_layout']:
            raw=[0]*788;packed=[0]*1024
            for beat in [1,0,0,1,0,1,1]:
                incoming=[rng.getrandbits(1) for _ in range(2048)]
                for b in range(788):
                    f=raw_global(leaf['leaf'],b)
                    if f//2048==beat:raw[b]=incoming[f%2048]
                for cw in leaf['codewords']:
                    if cw['beat']==beat:
                        values=[incoming[i] for _,i in bits(cw)]+[0]*cw['zero_pad']
                        # Systematic payload carrier tests mapping; SECDED math belongs codec gate.
                        packed[cw['code_offset']:cw['code_offset']+64]=values
                decoded=[None]*788
                for cw in leaf['codewords']:
                    for j,(b,_) in enumerate(bits(cw)):decoded[b]=packed[cw['code_offset']+j]
                self.assertEqual(decoded,raw)
if __name__=='__main__':unittest.main()
