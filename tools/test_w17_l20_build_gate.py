#!/usr/bin/env python3
"""Exercise W17 orchestration's real child-status and archive admission paths."""
import json
import hashlib
import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest

GATE = Path(__file__).with_name('w17_l20_build_gate.py')
spec = importlib.util.spec_from_file_location('w17_gate_under_test', GATE)
PRODUCTION = importlib.util.module_from_spec(spec)
spec.loader.exec_module(PRODUCTION)
DRIVER = '''import argparse,json,os,pathlib,subprocess,sys,time
p=argparse.ArgumentParser(); p.add_argument('step'); p.add_argument('--l20',action='store_true'); p.add_argument('--work'); p.add_argument('--only'); p.add_argument('--jobs'); a=p.parse_args()
time.sleep(float(os.environ.get('W17_GATE_TEST_SLEEP','0')))
rc=int(os.environ.get('W17_GATE_TEST_CHILD_RC','0'))
if rc: sys.exit(rc)
w=pathlib.Path(a.work); d=w/a.only; d.mkdir(parents=True)
src=d/'x.c'; src.write_text('int test_archive_member = 1;')
obj=d/(a.only.replace('die','Vdie')+'__fixture.o')
subprocess.run(['gcc','-c',str(src),'-o',str(obj)],check=True)
subprocess.run(['ar','rcs',str(d/(a.only.replace('die','Vdie')+'__ALL.a')),str(obj)],check=True)
print(json.dumps(dict(steps=[dict(log='verilate_'+a.only+'.log',returncode=0),dict(log='build_'+a.only+'.log',returncode=0)])))
'''


class GateTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='w17-gate-test-')
        self.root = Path(self.tmp.name)
        self.source = self.root/'source'; (self.source/'tools').mkdir(parents=True)
        (self.source/'tools/v41_die_rt.py').write_text(DRIVER)
        # Substitute only the identity constants for our disposable compiler
        # fixture; production policy logic and orchestration stay unchanged.
        self.fixture_old_sha = hashlib.sha256(b'old fixture driver').hexdigest()
        self.fixture_new_sha = hashlib.sha256(DRIVER.encode()).hexdigest()
        self.gate = self.root/'gate.py'
        self.gate.write_text(GATE.read_text().replace(PRODUCTION.DRIVER_OLD_SHA256, self.fixture_old_sha)
                             .replace(PRODUCTION.DRIVER_NEW_SHA256, self.fixture_new_sha))
        subprocess.run(['git','init','-q',str(self.source)],check=True)
        subprocess.run(['git','-C',str(self.source),'add','tools/v41_die_rt.py'],check=True)
        subprocess.run(['git','-C',str(self.source),'-c','user.name=W17 Test','-c','user.email=w17@example.invalid','commit','-qm','fixture'],check=True)
        self.work = self.root/'original'; self.work.mkdir()
        self.script = self.root/'original.sh'; self.script.write_text('wait\necho BUILT\n')
        self.pins = self.root/'pins.json'; self.pins.write_text(json.dumps({'tools/v41_die_rt.py':self.fixture_old_sha}))
        self.attempt = self.root/'attempt'
        for rank in (0,1,3):
            subprocess.run(['python3',str(self.source/'tools/v41_die_rt.py'),'build','--work',str(self.work),'--only',f'die{rank}'],check=True,stdout=subprocess.DEVNULL)
            steps=[]
            for kind in ('verilate','build'):
                log=f'{kind}_die{rank}.log'; (self.work/log).write_text('Exit status: 0\n')
                steps.append(dict(log=log,returncode=0))
            Path(f'{self.work}.b{rank}.log').write_text(json.dumps(dict(steps=steps)))
        Path(f'{self.work}.b2.log').write_text('original exit137\n')
        (self.work/'verilate_die2.log').write_text('Exit status: 137\n')

    def tearDown(self):
        self.tmp.cleanup()

    def run_gate(self, child_rc=0, extras=()):
        env=dict(os.environ,W17_GATE_TEST_CHILD_RC=str(child_rc))
        cmd=['python3',str(self.gate),'--source',str(self.source),'--adopt-work',str(self.work),
             '--attempt',str(self.attempt),'--original-script',str(self.script),'--expected-source-pins',str(self.pins),
             '--min-memory-gib','0','--min-disk-gib','0','--max-load','100000',*extras]
        result=subprocess.run(cmd,env=env,capture_output=True,text=True)
        return result, json.loads((self.attempt/'result.json').read_text())

    def test_success_requires_four_verified_archives(self):
        p,r=self.run_gate(); self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual(r['status'],'PASS'); self.assertEqual(len(r['ranks']),4)
        self.assertTrue((self.attempt/'BUILT').exists())
        self.assertEqual((self.attempt/'original_l20build.sh').read_bytes(),self.script.read_bytes())
        self.assertEqual((self.attempt/'original_rank2.driver.log').read_text(),'original exit137\n')
        self.assertEqual(r['driver_identity']['actual_sha256'], self.fixture_new_sha)
        self.assertEqual(r['source_sha256']['tools/v41_die_rt.py'], self.fixture_new_sha)

    def test_child_failure_never_writes_built(self):
        p,r=self.run_gate(child_rc=7); self.assertEqual(p.returncode,1)
        self.assertEqual(r['ranks']['2']['returncode'],7)
        self.assertFalse((self.attempt/'BUILT').exists())

    def test_corrupt_archive_rejects_before_retry(self):
        (self.work/'die1/Vdie1__ALL.a').write_bytes(b'bad archive')
        p,r=self.run_gate(); self.assertEqual(p.returncode,1)
        self.assertFalse((self.attempt/'rank2.driver.log').exists())
        self.assertFalse((self.attempt/'BUILT').exists())

    def test_failed_adopted_status_rejects_even_with_archive(self):
        p=Path(f'{self.work}.b1.log'); d=json.loads(p.read_text()); d['steps'][1]['returncode']=2; p.write_text(json.dumps(d))
        p,r=self.run_gate(); self.assertEqual(p.returncode,1)
        self.assertFalse((self.attempt/'BUILT').exists())

    def test_resource_deadline_never_launches_retry(self):
        p,r=self.run_gate(extras=('--min-memory-gib','1000000','--deadline-seconds','0'))
        self.assertEqual(p.returncode,1); self.assertIn('deadline',r['error'])
        self.assertFalse((self.attempt/'rank2.driver.log').exists())
        self.assertFalse((self.attempt/'BUILT').exists())

    def test_live_rank_blocks_retry_without_terminating_it(self):
        child=subprocess.Popen(['python3',str(self.source/'tools/v41_die_rt.py'),'build',
                                '--work',str(self.work),'--only','die2'],
                               env=dict(os.environ,W17_GATE_TEST_SLEEP='60'),stdout=subprocess.DEVNULL)
        try:
            # cmdline is visible as soon as Popen returns; deadline exits on the
            # first live-process observation, leaving our fixture child alive.
            p,r=self.run_gate(extras=('--deadline-seconds','0'))
            self.assertEqual(p.returncode,1)
            self.assertIsNone(child.poll())
            self.assertFalse((self.attempt/'rank2.driver.log').exists())
            self.assertFalse((self.attempt/'BUILT').exists())
            self.assertIn('WAIT_LIVE_RANKS',(self.attempt/'events.jsonl').read_text())
        finally:
            child.terminate(); child.wait()  # this test's own disposable fixture

    def test_arbitrary_clean_driver_rewrite_is_refused(self):
        driver=self.source/'tools/v41_die_rt.py'
        driver.write_text(DRIVER+'\n# arbitrary rewrite outside the attestation\n')
        subprocess.run(['git','-C',str(self.source),'add','tools/v41_die_rt.py'],check=True)
        subprocess.run(['git','-C',str(self.source),'-c','user.name=W17 Test','-c','user.email=w17@example.invalid',
                        'commit','-qm','arbitrary rewrite'],check=True)
        p,r=self.run_gate(); self.assertEqual(p.returncode,1)
        self.assertIn('unattested driver identity',r['error'])
        self.assertFalse((self.attempt/'rank2.driver.log').exists())
        self.assertFalse((self.attempt/'BUILT').exists())

    def test_production_allows_only_exact_attested_identities(self):
        old,new=PRODUCTION.DRIVER_OLD_SHA256,PRODUCTION.DRIVER_NEW_SHA256
        for expected,actual in ((old,old),(old,new),(new,new)):
            self.assertEqual(PRODUCTION.driver_identity(expected,actual)['actual_sha256'],actual)
        for expected,actual in ((old,'f'*64),('f'*64,new),(new,old)):
            with self.assertRaises(ValueError): PRODUCTION.driver_identity(expected,actual)


if __name__ == '__main__':
    unittest.main()
