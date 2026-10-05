"""Static preparation checks only; no compiler, elaborator, simulator or systemd call."""
import importlib.util
import json
from pathlib import Path
import re
import unittest
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
def load(name,p):
    s=importlib.util.spec_from_file_location(name,ROOT/p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
P=load('primitive_prepare','tools/prepare_dsrom_bmul_rne_primitive.py')
D=load('source_diagnosis','tools/diagnose_dsrom_numerical_bf_error.py')
C=load('correct_encode_model','tools/model_dsrom_bmul_subnormal.py')
G=load('golden_primitive_static','tools/hdc_golden.py')
def enc_mut(name,sign,be,sig):
    if name=='shift_offbyone':be-=1
    shift=1-be
    if shift<1 or shift>24:return sign<<31 if name=='negative_zero' else 0
    main=sig>>shift;guard=(sig>>(shift-1))&1;sticky=bool(sig&((1<<(shift-1))-1))
    inc=0 if name=='truncation' else guard if name=='tie_away' else int(guard and (sticky or main&1))
    rounded=main+inc
    return (sign<<31)|rounded if rounded or name=='negative_zero' else 0

def product_mut(name,a,b):
    nf=(a&0x7f80)==0x7f80 or (b&0x7f80)==0x7f80;zero=(a&0x7fff)==0 or (b&0x7fff)==0
    y,e=P.expected(a,b)
    if name=='zero_nonfinite_bypass' and zero:return 0,0
    if name=='refusal_no_fault' and e:return 0,0
    if nf or zero:return y,e
    sa,ea=C.decode(a);sb,eb=C.decode(b);pq=sa*sb;be=ea+eb+(128 if pq&32768 else 127)
    if be>254:return y,e
    if name=='old_range' and be<-6:return 0,1
    if be<=0:
        if name=='underflow_fault':return y,1
        return enc_mut(name,(a^b)>>15,be,pq<<(8 if pq&32768 else 9)),0
    return y,e
class PrimitivePrepareTests(unittest.TestCase):
    def test_independent_expected_matches_pinned_golden(self):
        for a,b in P.inputs():
            y,e=P.expected(a,b)
            if (a&0x7f80)==0x7f80 or (b&0x7f80)==0x7f80:self.assertEqual((0,1),(y,e));continue
            with np.errstate(under='ignore',over='ignore',invalid='ignore'):
                val=G.mul(G.from_bits(a<<16),G.from_bits(b<<16))
            self.assertEqual((0,1) if np.isinf(val) else (int(G.bits(val)),0),(y,e))
    def test_negative_baseline_witnesses_and_corrected_RNE(self):
        for i in (0,1):
            a,b=P.inputs()[i];old=D.bmul_stages(a,b)
            self.assertEqual(('00000000',1),(old['s4_y'],old['s5_fault']))
            self.assertEqual(0,P.expected(a,b)[1])
        self.assertEqual((0x8000,0),P.expected(0x0080,0x3b80))
        self.assertEqual((0,0),P.expected(0x8080,0x3380))
    def test_reduced_category_proof_and_generic_normal_carry(self):
        proof=C.proof();self.assertEqual(65536,proof['BF_decode_codes']);self.assertEqual(819200,proof['sign_checks'])
        self.assertEqual(0x800000,C.corrected_encode(0,0,0xffffff))
    def test_each_mutant_has_explicit_static_counterexample(self):
        for name in P.MUTANTS:
            hits=[i for i,(a,b) in enumerate(P.inputs()) if product_mut(name,a,b)!=P.expected(a,b)]
            ehits=[i for i,(s,be,sig) in enumerate(P.encoder_inputs()) if enc_mut(name,s,be,sig)!=C.corrected_encode(s,be,sig)]
            self.assertTrue(hits or ehits,name)
    def test_input_and_assertion_images_separate(self):
        self.assertEqual(P.input_svh(),(ROOT/'rtl/test/dsrom_bmul_rne_primitive_inputs.svh').read_text())
        self.assertEqual(P.expected_svh(),(ROOT/'rtl/test/dsrom_bmul_rne_primitive_expected.svh').read_text())
        bench=(ROOT/'rtl/test/tb_dsrom_bmul_rne_primitive.sv').read_text()
        self.assertIn('a={inp[31:16],16\'d0};b={inp[15:0],16\'d0}',bench)
        self.assertNotRegex(bench,r'(a|b|esig|ebe|esign)\s*=\s*(product_expected|encoder_expected|expectation|eexpect)')
        self.assertIn('rst_n=1;#1;rst_n=0;#1;',bench)
        self.assertIn('mutant missing explicit DIFF',bench);self.assertIn('negative baseline witness missing',bench)
    def test_state_ports_latency_default_and_preservation(self):
        old=(ROOT/'rtl/v41rom/ot_v41_bmul2.sv').read_text();new=(ROOT/'rtl/v41rom/ot_v41_bmul2_rne_prepare.sv').read_text()
        self.assertIn('parameter integer GRADUAL_RNE = 0',new)
        self.assertEqual(re.findall(r'^    reg .*;',old,re.M),re.findall(r'^    reg .*;',new,re.M))
        self.assertEqual(re.findall(r'^    (?:input|output).*',old,re.M),re.findall(r'^    (?:input|output).*',new,re.M))
        self.assertEqual(old.count('always @(posedge'),new.count('always @(posedge'))
        self.assertNotIn('reg ',(ROOT/'rtl/v41rom/ot_v41_bmul_subnormal_rne_prepare.sv').read_text())
        P.verify()
    def test_namespace_and_mutant_changes_are_local(self):
        pkg=P.files();numerical=load('numerical_sources','tools/prepare_dsrom_actual_element_numerical.py').package()
        for n in ('ref_ot_prefix.sv','cand_ot_prefix.sv'):self.assertEqual(numerical[n],pkg[n])
        for prefix in ('ref_','cand_'):
            self.assertEqual(P.namespace((ROOT/'rtl/v41rom/ot_v41_bmul2_rne_prepare.sv').read_text(),prefix),pkg[prefix+'ot_v41_bmul2_rne_prepare.sv'])
        self.assertEqual(26,len(pkg))
if __name__=='__main__':unittest.main()
