import importlib.util
import json
import re
import copy
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('prep',ROOT/'tools/prepare_dsrom_cadence_admission.py')
P=importlib.util.module_from_spec(spec);spec.loader.exec_module(P)
A=P.A


class AdmissionPreparation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.files=P.package()
        cls.plan=json.loads((ROOT/'results/rtl/dsrom_upstream_pair_cadence_runner_prepare_r3_20261002/runner_plan.json').read_text())
        original=(ROOT/'results/rtl/dsrom_upstream_pair_cadence_execution_r3_20261002/existing_fast8_simulate.log').read_text()
        edges=[int(re.search(r'cycle=(\d+)',s)[1]) for s in original.splitlines() if s.startswith('EDGE ')]
        trace=P.TRACE.loader_trace(13,max(edges))
        lines=[]
        for line in original.splitlines():
            lines.append(line)
            if line.startswith('EDGE '):
                c=int(re.search(r'cycle=(\d+)',line)[1]);e=trace[c-1]
                lines.append(f"LOADER cycle={c} valid={e['c_v']} addr={e['c_a']} ld_run={e['ld_run']} ld_k={e['ld_k']}")
        cls.fixture='\n'.join(lines)

    def test_source_binding_LAT(self):
        b=A.actual_binding();self.assertEqual((b['FAST'],b['PP'],b['CUT'],b['actual_add_LAT']),(1,1,379,8))

    def test_stale_profile_refused(self):
        with self.assertRaisesRegex(ValueError,'STALE_IMAGE_ADMISSION'):
            P.package('production5')

    def test_stale_metadata_refused(self):
        j={'params':{'FAST':1,'PP':1,'BP':0,'FRONT_PAR':0,'actual_add_LAT':5},'phases':[{}]}
        with self.assertRaisesRegex(ValueError,'actual_add_LAT'):
            A.refuse_stale(j,A.actual_binding())

    def test_missing_binding_refused(self):
        with self.assertRaisesRegex(ValueError,'STALE_IMAGE_ADMISSION'):
            A.refuse_stale({'params':{},'phases':[{}]},A.actual_binding())

    def test_immutable_ROM_VM_control_inputs(self):
        old=P.OLD.package()
        for name,text in self.files.items():
            if name.startswith('existing_fast8/') or name=='dsrom_upstream_pair_ROM.cpp':
                self.assertEqual(text,old[name],name)
        self.assertFalse(any(p.startswith('production5/') for p in self.files))

    def test_engine_sources_unchanged(self):
        old=P.OLD.package()
        for name,text in self.files.items():
            if name.endswith('.sv') and not name.startswith('tb_'):
                self.assertEqual(text,old[name],name)

    def test_golden_assertions_unchanged(self):
        old=(ROOT/P.OLD.BENCH).read_text();new=(ROOT/P.BENCH).read_text()
        for line in old.splitlines():
            if any(marker in line for marker in ('44000000','PUBLIC_ORACLE_DIFFERENCE','EMITTED_ORDER','CONTROL_COVERAGE','IDLE_MACRO_EMITTED')):
                self.assertIn(line,new)
        self.assertEqual(P.expected(),P.OLD.expected())

    def test_exclusive_fault_branch_and_settle(self):
        text=(ROOT/P.BENCH).read_text()
        self.assertIn('end else begin\n      if(p_fault || s_fault)',text)
        self.assertIn('u_pair.c_v && u_pair.c_a>=25',text)
        self.assertIn('#415;clk=0;#1;cycles=cycles+1;',text)
        self.assertIn('clk=1;#1;',text)
        self.assertIn('profile!=8)$fatal(1,"STALE_IMAGE_ADMISSION_PROFILE")',text)

    def test_fixture_control_and_exact_loader_counts(self):
        # Parser fixture only: old runtime control plus SOURCE-DERIVED loader
        # markers. This does not claim new observed HDL loader coverage.
        r=P.completion(self.fixture,self.plan,0)
        self.assertTrue(r['valid'],r)
        self.assertEqual((r['loader_samples'],r['valid_config_writes']),(1029,25))

    def test_valid25_loader_mutant_rejected(self):
        text=self.fixture.replace('valid=0 addr=25','valid=1 addr=25',1)
        self.assertFalse(P.completion(text,self.plan,0)['valid'])

    def test_missing_duplicate_malformed_loader(self):
        line=next(s for s in self.fixture.splitlines() if s.startswith('LOADER'))
        for text in (self.fixture.replace(line,'',1),self.fixture+'\n'+line,self.fixture+'\nLOADER malformed'):
            with self.subTest(text=text[-100:]):
                self.assertFalse(P.completion(text,self.plan,0)['valid'])

    def test_public_or_terminal_mutant_rejected(self):
        for text in (self.fixture.replace('value=44000000','value=44000001',1),self.fixture+'\nPASS_FOREIGN',self.fixture+'\n%Fatal unexpected'):
            with self.subTest(text=text[-100:]):
                self.assertFalse(P.completion(text,self.plan,0)['valid'])

    def test_transcription_excludes_payload_only(self):
        for module in (A.FAST,A.PROD):
            fn,pins=A.metadata_function(module)
            self.assertEqual(len(pins['omitted_payload_sha256']),2 if module is A.FAST else 1)
            self.assertIn('no state/geometry/order/demand reductions',pins['excluded'])

    def test_forged_LAT_tag_cannot_admit_stale_stream(self):
        files,ph,rom=P.OLD.images('existing_fast8')
        ph=dict(ph,pc=0,kind='qe',key=0)
        meta=dict(params=dict(np=8192,regions=128,nbf=1024,active=8192,depth=8192,
                             FAST=1,PP=1,BP=0,FRONT_PAR=0,actual_add_LAT=8),
                  phases=[ph],stream_words=64)
        stream=[int(s,16) for s in files['spine_stream.hex'].splitlines()]
        headers=[int(s,16) for s in files['spine_phase.hex'].splitlines()]
        r=A.verify_phase_images(meta,stream,headers)
        self.assertEqual(r['stream_words'],64)
        old,_,_=P.OLD.images('production5')
        with self.assertRaisesRegex(ValueError,'source round stream differs'):
            A.verify_phase_images(meta,[int(s,16) for s in old['spine_stream.hex'].splitlines()],headers)
        bad=copy.deepcopy(meta);bad['phases'][0]['nbeat']=40
        with self.assertRaisesRegex(ValueError,'phase cycle count differs'):
            A.verify_phase_images(bad,stream,headers)
        wrong=list(headers);wrong[0]^=1<<14
        with self.assertRaisesRegex(ValueError,'source phase words differs|source phase words differ'):
            A.verify_phase_images(meta,stream,wrong)


if __name__=='__main__':
    unittest.main()
