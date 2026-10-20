#!/usr/bin/env python3
"""Payload verdict, coverage, shell status aggregation, and MU payload-contract regressions."""
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

Q = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('checker', Q / 'mu_check.py')
checker = importlib.util.module_from_spec(spec); spec.loader.exec_module(checker)

class Admission(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.r = Path(self.tmp.name)
        self.g = {'beats': 2, 'instances': [{'inst': 0, 'start': 10, 'kind': 'AG', 'name': 'test'}]}
        self.log = ('LAND 0 0 1 0 10 20 22\nLAND 0 0 1 1 11 21 23\n'
                    'XDIE_STATS beats 2 landed 2 mismatches 0 late 0 maxlate -2 extra 0 faults 0000000000000000 live 64/64 last_cycle 21\n'
                    'PASS xdie_s81: 2 beats\n')
    def tearDown(self): self.tmp.cleanup()
    def check(self, log, golden=None):
        (self.r/'golden.json').write_text(json.dumps(golden or self.g)); (self.r/'run.log').write_text(log)
        p = subprocess.run([sys.executable, str(Q/'mu_check.py'), str(self.r), str(self.r/'run.log'), '--json', str(self.r/'check.json')], capture_output=True, text=True)
        return p, json.loads((self.r/'check.json').read_text())
    def test_complete_pass(self):
        p,r=self.check(self.log); self.assertEqual(p.returncode,0,p.stdout); self.assertTrue(r['qualified'])
    def test_timing_pass_payload_fail(self):
        p,r=self.check(self.log.replace('mismatches 0','mismatches 1').replace('PASS xdie_s81','FAIL xdie_s81'))
        self.assertNotEqual(p.returncode,0); self.assertTrue(r['win_pass']); self.assertTrue(r['inv_pass']); self.assertFalse(r['functional_pass'])
    def test_missing_terminal_verdict(self):
        p,r=self.check(self.log.split('PASS xdie_s81')[0]); self.assertNotEqual(p.returncode,0)
    def test_pass_label_cannot_hide_mismatches(self):
        p,r=self.check(self.log.replace('mismatches 0','mismatches 1')); self.assertNotEqual(p.returncode,0)
    def test_missing_land(self):
        p,r=self.check(self.log.replace('LAND 0 0 1 1 11 21 23\n','')); self.assertNotEqual(p.returncode,0); self.assertFalse(r['coverage_pass'])
    def test_duplicate_land(self):
        p,r=self.check(self.log.replace('LAND 0 0 1 1 11 21 23','LAND 0 0 1 0 10 20 22')); self.assertNotEqual(p.returncode,0); self.assertFalse(r['coverage_pass'])
    def test_unassigned_land(self):
        p,r=self.check(self.log.replace('LAND 0 0 1 1','LAND 99 0 1 1')); self.assertNotEqual(p.returncode,0)
    def test_early_mutant(self):
        p,r=self.check(self.log.replace('10 20 22','10 19 22')); self.assertNotEqual(p.returncode,0); self.assertFalse(r['win_pass'])
    def test_record_refuses_failed_payload(self):
        self.check(self.log.replace('PASS xdie_s81','FAIL xdie_s81'))
        p=subprocess.run([sys.executable,str(Q/'record.py'),'--golden',str(self.r/'golden.json'),'--run',str(self.r/'run.log'),'--name','bad','--out',str(self.r/'record.json'),'--compose'],capture_output=True,text=True)
        self.assertNotEqual(p.returncode,0); self.assertIn('REFUSED',p.stderr); self.assertFalse((self.r/'record.json').exists())
    def test_record_refuses_incomplete_coverage(self):
        self.check(self.log.replace('LAND 0 0 1 1 11 21 23\n',''))
        p=subprocess.run([sys.executable,str(Q/'record.py'),'--golden',str(self.r/'golden.json'),'--run',str(self.r/'run.log'),'--name','bad','--out',str(self.r/'record.json'),'--compose'],capture_output=True,text=True)
        self.assertNotEqual(p.returncode,0); self.assertIn('REFUSED',p.stderr)
    def test_mu_spare_only_changes_reserved_bits(self):
        for name,extra in [('legacy',[]),('mu',['--reserve-mu-tag'])]:
            subprocess.run([sys.executable,str(Q/'gen_golden.py'),'--out',str(self.r/name),'--only','router_allgather','--reps','1','--dl-model','fluid',*extra],check=True,capture_output=True)
        legacy=(self.r/'legacy/stim.hex').read_text().splitlines(); mu=(self.r/'mu/stim.hex').read_text().splitlines(); mask=((1<<33)-1)<<1045
        self.assertEqual(len(legacy),len(mu)); self.assertTrue(any(int(x,16)&mask for x in legacy))
        for a,b in zip(legacy,mu): self.assertEqual(int(b,16),int(a,16)&~mask)
        self.assertNotIn('payload_contract',json.loads((self.r/'legacy/golden.json').read_text()))
        self.assertTrue(json.loads((self.r/'mu/golden.json').read_text())['payload_contract']['reserved'])
    def gate(self,build=0,run=0,check=0):
        dest=self.r/'tools/xdie_s81_2';dest.mkdir(parents=True)
        for f in ['gate_mu.sh','gate_result.sh']:shutil.copy2(Q/f,dest/f)
        (dest/'xdie2.sh').write_text(f'''#!/bin/bash
if [ "$1" = build ]; then exit {build}; fi
mkdir -p "$2/$4"; echo RUN >> calls; echo 'PASS xdie_s81: fake' > "$2/$4/run.log"; echo BENCH_PASS; exit {run}
''')
        (dest/'mu_check.py').write_text(f'raise SystemExit({check})\n')
        p=subprocess.run(['bash','tools/xdie_s81_2/gate_mu.sh','out','u'],cwd=self.r,capture_output=True,text=True)
        return p
    def test_gate_build_fail_stops_runs(self):
        self.assertNotEqual(self.gate(build=3).returncode,0);self.assertFalse((self.r/'calls').exists())
    def test_gate_run_fail_not_hidden_by_check_pass(self):
        self.assertNotEqual(self.gate(run=1).returncode,0);self.assertTrue((self.r/'out/DONE_u_FAILED').exists());self.assertFalse((self.r/'out/DONE_u').exists())
    def test_gate_check_fail_not_hidden_by_gzip(self):
        self.assertNotEqual(self.gate(check=1).returncode,0);self.assertFalse((self.r/'out/DONE_u').exists())
    def test_gate_all_pass(self):
        p=self.gate();self.assertEqual(p.returncode,0,p.stderr);self.assertTrue((self.r/'out/DONE_u').exists());self.assertEqual(len((self.r/'calls').read_text().splitlines()),6)

if __name__=='__main__': unittest.main(verbosity=2)
