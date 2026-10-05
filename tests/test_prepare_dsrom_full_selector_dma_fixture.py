import importlib.util
import json
from pathlib import Path
import struct
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('fixture',ROOT/'tools/prepare_dsrom_full_selector_dma_fixture.py')
M=importlib.util.module_from_spec(spec);spec.loader.exec_module(M)

class Fixture(unittest.TestCase):
    def test_full_geometry_and_coverage(self):
        self.assertEqual(len(M.cases()),37)
        self.assertEqual({n for n,_,_ in M.cases()},{512,2048})
        self.assertIn((2048,8192,'signed_boundaries'),M.cases())
        text=(ROOT/M.TEMPLATE).read_text()
        self.assertEqual(text.count('.TK_NMAX(2048),.TK_DIG(8)'),2)
        self.assertEqual(text.count('.GW(4)'),2)
        self.assertIn('TK_BALANCED(1)',text)
    def test_native_packed_rank_word_ownership(self):
        for n in (512,2048):
            raw=list(range(4*n));beats=M.operands(n,raw)
            self.assertEqual(len(beats),2*n//16)
            for j,b in enumerate(beats):
                half=j//(n//16);word=j%(n//16)
                for r in range(4):
                    for lane in range(16):
                        got=(b>>(32*(16*r+lane)))&0xffffffff
                        self.assertEqual(got,word*16+lane+(r*n if half==0 else 0))
    def test_oracle_independent_order_key_and_padding(self):
        for n,k,pattern in M.cases():
            raw=M.scores(n,pattern);result=M.expected(n,k,raw)
            floats=[struct.unpack('!f',struct.pack('!I',w))[0] for w in raw]
            ranked=sorted(zip(floats,[(i//n)*2*n+i%n for i in range(4*n)]),key=lambda x:(-x[0],x[1]))
            target=sorted(i for _,i in ranked[:k])+[0]*((-k)%16)
            flat=[(word>>(32*i))&0xffffffff for word in result for i in range(16)]
            self.assertEqual(flat,target)
            self.assertLessEqual(len(result),512)
    def test_prior_source_proof_operand_pins(self):
        proof=json.loads((ROOT/M.MODELS[1]).read_text())
        self.assertEqual(len(proof['cases']),len(M.cases()))
        for record,(n,k,pattern) in zip(proof['cases'],M.cases()):
            self.assertEqual((record['runtime_n'],record['k'],record['pattern']),(n,k,pattern))
            words=M.scores(n,pattern)
            self.assertEqual(M.sha(struct.pack('<'+str(len(words))+'I',*words)),record['operand_sha256'])

    def test_signed_zero_tie_and_infinities(self):
        raw=[0x80000000,0,0x7f800000,0xff800000]*512
        self.assertEqual(M.expected(512,1,raw)[0],2)
        with self.assertRaisesRegex(ValueError,'NaN'):M.expected(512,1,[0x7fc00001]*2048)
    def test_assertions_never_drive_dut_inputs(self):
        text=(ROOT/M.TEMPLATE).read_text()
        self.assertEqual(text.count('assertions['),3) # declaration and two comparisons
        for line in text.splitlines():
            if 'assertions[' in line and 'reg ' not in line:self.assertIn('$fatal',line)
        self.assertIn('o_data=operands[beat]',text)
        self.assertNotIn('.o_data(assertions',text)
    def test_settling_capture_and_reset_calibration(self):
        text=(ROOT/M.TEMPLATE).read_text()
        self.assertLess(text.index('ref_saved_we[ref_groups]=ref_we'),text.index('#1;\n      if(ref_fault'))
        self.assertIn('@(negedge clk);#1;',text)
        self.assertIn('#1;\n    if(ref_we!==0',text)
        self.assertIn('cand_retire-ref_retire!=368',text)
        self.assertIn('cycle-ref_saved_cycle[cand_groups]!=368',text)
        self.assertIn('repeat(3) tick();',text)
        self.assertEqual(text.count('reset_fixture();observe_reset_drain();'),4)
        self.assertIn('RESET_REAPPEAR_DIFF',text)
        self.assertIn('#416 clk=1; #417 clk=0;',text)
    def test_fresh_reproduction_pins_and_readiness(self):
        with tempfile.TemporaryDirectory() as t:
            a=Path(t)/'a';b=Path(t)/'b';plan=M.prepare(a);M.prepare(b)
            self.assertEqual((a/'artifact_manifest.json').read_bytes(),(b/'artifact_manifest.json').read_bytes())
            manifest=json.loads((a/'artifact_manifest.json').read_text())
            for p,h in manifest.items():self.assertEqual(M.sha((a/p).read_bytes()),h)
            self.assertFalse(plan['compile_admitted']);self.assertFalse(plan['RTL_equivalence'])
            self.assertIn('ot_w15_coll_dma_balanced_station_prepare',plan['missing_compile_modules'])
            calls=(a/'case_calls.svh').read_text().splitlines()
            self.assertEqual(len(calls),41)
            self.assertEqual(calls[-4:],[f'run_case(5,512,2048,{p});' for p in range(1,5)])
            with self.assertRaisesRegex(ValueError,'fresh'):M.prepare(a)
    def test_corrupted_source_refused(self):
        prior=M.PINS.copy()
        try:
            M.PINS[next(iter(M.PINS))]='0'*64
            with tempfile.TemporaryDirectory() as t:
                with self.assertRaisesRegex(ValueError,'pin changed'):M.prepare(Path(t)/'out')
        finally:M.PINS=prior

if __name__=='__main__':unittest.main()
