"""Exact numerical-contract and preparation checks only; no HDL execution."""
import importlib.util
import json
import random
import re
import sys
import unittest
from fractions import Fraction
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import hdc_golden_v41 as GOLD
import prepare_dsrom_actual_element_numerical as PREP
O=PREP.ORACLE
IMAGE=PREP.inputs()
ROWS=O.expected(IMAGE)
BENCH=(ROOT/'rtl/test/tb_dsrom_actual_element_numerical.sv').read_text()
OLD=(ROOT/'rtl/test/tb_dsrom_actual_element_gate_rowfix.sv').read_text()
def golden_terms(r):
    """Decode input words independently; use pinned golden operations/order."""
    p=IMAGE['profiles'][r['phase']];terms=[]
    for local in range(p['units_per_segment']):
        unit=r['segment_slot']*p['units_per_segment']+local
        for chunk in range(16 if p['family']=='bf16' else 2):
            for block in range(8):
                addr=O.word_address(p,r['segment_slot'],local,block,chunk if p['family']=='fp8' else 0)
                w=int(IMAGE['ROM_words'][str(r['macro'])][str(addr)],16)
                if p['family']=='bf16':
                    terms.append(GOLD.mul(GOLD.from_bits(((w>>(16*chunk))&65535)<<16),GOLD.from_bits(O.xbcode(r['position'],unit,block,chunk)<<16)))
                else:
                    fp4=p['family']=='fp4';start=136*chunk if fp4 else 0;stride=4 if fp4 else 8
                    # E4 exact codes <=9 bits; 32 products fit binary64 exactly (<=42 significant bits).
                    x=np.array([float(O.e4m3(O.xcode(r['position'],unit,block,l,chunk))) for l in range(32)],dtype=np.float64)
                    weights=np.array([float(O.e2m1((w>>(start+stride*l))&15) if fp4 else O.e4m3((w>>(8*l))&255)) for l in range(32)],dtype=np.float64)
                    dot=np.float32(np.dot(x,weights));scale=((w>>(128+136*chunk if fp4 else 256))&255)-127+O.xexp(r['position'],unit,block,chunk)
                    terms.append(np.float32(np.ldexp(dot,scale)))
    return np.array(terms,dtype=np.float32)
def mismatches(mutant):
    return [dict(phase=r['phase'],macro=r['macro'],segment=r['segment_slot'],position=r['position'],expected=r['value_hex'],mutant=f'{O.partial(IMAGE,r["phase"],r["macro"],r["segment_slot"],r["position"],mutant):08x}') for r in ROWS if O.partial(IMAGE,r['phase'],r['macro'],r['segment_slot'],r['position'],mutant)!=int(r['value_hex'],16)]
class NumericalTests(unittest.TestCase):
    def test_exhaustive_code_decode(self):
        for c in range(256):
            if c&127==127:
                with self.assertRaises(ValueError):O.e4m3(c)
                continue
            e=(c>>3)&15;frac=(c&7)/8.0
            value=(-1 if c&128 else 1)*(frac*2**-6 if e==0 else (1+frac)*2**(e-7))
            self.assertEqual(Fraction(value),O.e4m3(c))
        for c in range(16):self.assertEqual(Fraction((0,.5,1,1.5,2,3,4,6)[c&7])*(-1 if c&8 else 1),O.e2m1(c))
    def test_rounding_ties_subnormal_and_zero_contract(self):
        self.assertEqual(0x3f800000,O.round32(1+O.pow2(-24)))
        self.assertEqual(0x3f800002,O.round32(1+3*O.pow2(-24)))
        self.assertEqual(0,O.round32(O.pow2(-150)))
        self.assertEqual(2,O.round32(3*O.pow2(-150)))
        self.assertEqual(0x00800000,O.round32(O.pow2(-126)-O.pow2(-150)))
        self.assertEqual(0,O.add(0x80000000,0x80000000))
        with self.assertRaises(ValueError):O.round32(O.pow2(128))
    def test_binary32_primitive_crosscheck_against_pinned_golden(self):
        rng=random.Random(20261002)
        for i in range(400):
            a=(rng.randrange(2)<<31)|(rng.randrange(151)<<23)|rng.randrange(1<<23)
            b=(rng.randrange(2)<<31)|(rng.randrange(151)<<23)|rng.randrange(1<<23)
            for oracle,golden in ((O.add,GOLD.add),(O.mul,GOLD.mul)):
                self.assertEqual(int(GOLD.bits(golden(GOLD.from_bits(a),GOLD.from_bits(b)))),oracle(a,b))
    def test_all440_public_partials_against_independent_golden_chunk8(self):
        self.assertEqual(440,len(ROWS))
        self.assertEqual(8,GOLD.CHUNK)
        for row in ROWS:
            with self.subTest(phase=row['phase'],macro=row['macro'],segment=row['segment_slot'],position=row['position']):
                self.assertEqual(int(row['value_hex'],16),int(GOLD.bits(GOLD.csum(golden_terms(row)))))
    def test_parent_Ksplit_tree_and_BF16_boundary(self):
        parents=O.parent_rows(IMAGE,ROWS)
        for parent in parents:
            parts=sorted([r for r in ROWS if (r['phase'],r['macro'],r['row'],r['position'])==(parent['phase'],parent['macro'],parent['row'],parent['position'])],key=lambda r:r['lo'])
            terms=np.concatenate([golden_terms(r) for r in parts]);result=GOLD.csum(terms)
            self.assertEqual(int(parent['value_hex'],16),int(GOLD.bits(result)))
            self.assertEqual(int(parent['bf16_hex'],16),int(GOLD.bits(GOLD.to_bf16(result))))
            self.assertEqual(list(range(parent['nseg'])),[r['lo'] for r in parts])
        lo0=(5<<29)|(0x100<<13)|2;lo1=lo0|(1<<8)
        self.assertEqual(1<<8,(lo0^lo1));self.assertEqual(2,lo0&31)
    def test_numerical_negative_mutants_explicitly_differ(self):
        for mutant in ('exponent_offbyone','round_each_product','chunk_order_reversed','BF_lane_reversed','tree_lane_order_interleaved','segment_order_interleaved'):
            with self.subTest(mutant=mutant):self.assertTrue(mismatches(mutant),'no numerical witness for '+mutant)
    def test_input_packing_PP_parity_and_immutable_CPP(self):
        self.assertEqual(IMAGE,json.loads(json.dumps(O.build_inputs())))
        for p in IMAGE['profiles']:
            if p['empty']:continue
            addresses=[O.word_address(p,s,u,b,h) for b in range(8) for s in range(p['active_segments']) for u in range(p['units_per_segment']) for h in range(2 if p['family']=='fp8' else 1)]
            self.assertEqual(list(range(p['word_base'],p['word_base']+len(addresses))),addresses)
            self.assertTrue(all(a//2<4096 for a in addresses))
            for a in addresses:
                for macro in ('0','1'):self.assertLess(int(IMAGE['ROM_words'][macro][str(a)],16),1<<274)
        cpp=(ROOT/'rtl/test/dsrom_actual_element_numerical_rom.cpp').read_text()
        self.assertEqual(PREP.cpp(IMAGE),cpp)
        self.assertNotIn('numerical_expected',cpp);self.assertNotIn('independent_expected',cpp)
    def test_fixture_guards_geometry_reset_and_DIFFERENTIAL_preserved(self):
        task=lambda t:t.split('    task compare_all;',1)[1].split('    endtask',1)[0]
        self.assertEqual(task(OLD),task(BENCH));self.assertEqual(72,task(BENCH).count('"DIFF '))
        for text in ('#415;clk=0;#1;cycles=cycles+1;compare_all();','rst_n=0;#1;compare_all();','.NSEG(8),.NCH(16),.XF(XF),.LV(5),.BF16(BF),.MTP(1),.EARLY(1),.FAST(1),.PP(1),.BP(0),.PHW(6),.FIX_SECOND_ROW_INDEX(1)'):
            self.assertIn(text,BENCH)
        for text in ('NUMERICAL duplicate output','NUMERICAL missing/idle output','NUMERICAL metadata','NUMERICAL output before final block input','NUMERICAL exact coverage counters','gate latch behavior','legal drain/fault/quiet','inactive second row emitted','reset drain'):
            self.assertIn(text,BENCH)
        self.assertIn('oracle_rows!=(BF?456:344)',BENCH)
        self.assertIn('oracle_configs!=32*(BF?14:11)',BENCH)
    def test_expected_assertion_only_dataflow_and_case_coverage(self):
        self.assertEqual(1,BENCH.count('expected_word=numerical_expected('))
        for line in BENCH.splitlines():
            if re.search(r'\b(xs_|xb_|cfg_|go).*=',line):self.assertNotIn('numerical_expected(',line)
        for phase in (7,8,10,11):self.assertEqual(set(range(6)),{r['position'] for r in ROWS if r['phase']==phase})
        self.assertEqual(set(range(8)),{r['segment_slot'] for r in ROWS if r['phase']==1})
        self.assertEqual(set(range(4)),{r['segment_slot'] for r in ROWS if r['phase']==9})
    def test_authoritative_pins_and_unchanged_engine_package(self):
        PREP.verify();package=PREP.package();old=PREP.mod('old_prep','tools/prepare_dsrom_actual_element_rowfix.py').files()
        self.assertEqual(44,len(package))
        for name,text in old.items():
            if name not in ('tb_dsrom_actual_element_gate_rowfix.sv','dsrom_actual_element_rom.cpp'):self.assertEqual(text,package[name])
if __name__=='__main__':unittest.main()
