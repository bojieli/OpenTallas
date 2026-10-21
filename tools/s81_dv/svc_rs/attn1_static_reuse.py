#!/usr/bin/env python3
"""Replay source-matched V5.050 NT1 static fixtures without rebuilding binaries.

Requires the exact binaries recorded below, not arbitrary source-compatible builds.
Records mutant escape explicitly and returns nonzero for any unexpected outcome.
"""
import argparse, hashlib, json, pathlib, subprocess
HASHES = {
 0: 'e1544d9453f71bb0f8892ac6800f6d83945aeb13f1f7846a78a7431bd0555fbd',
 1: '245ecc074a0466df32cfe3fdbbd990e2cb87187245a504f82194c3fbf2d33270',
 2: 'dd6c863772b0034c7ca4253a4804f13a2c488d8c94f772aacaf8532b1e8cbf02',
 3: 'd704ba35dc1030e9a9d0b493b12fcbf708b389970a43cd68f1c866e9a16cadb7'}
CASES = {
 0: [('tail1',1,300,800),('tail33',33,300,800),('tail46',46,300,800),('full640_seed2',640,300,800)],
 1: [('tail46',46,300,800)], 2: [('tail46',46,300,800)],
 3: [('full640',640,300,800)]}
p=argparse.ArgumentParser();p.add_argument('--mutant',type=int,choices=HASHES,required=True);p.add_argument('--binary',type=pathlib.Path,required=True);p.add_argument('--out',type=pathlib.Path,required=True)
a=p.parse_args();a.binary=a.binary.resolve();a.out.mkdir(parents=True,exist_ok=True)
sha=hashlib.sha256(a.binary.read_bytes()).hexdigest()
if sha != HASHES[a.mutant]: raise SystemExit(f'REFUSED binary SHA {sha}')
rows=[]
for name,t,pr,pd in CASES[a.mutant]:
 args=[str(a.binary),'+static=1',f'+t={t}',f'+p0r={pr}',f'+p0d={pd}','+pace=4','+maxcyc=5000',f'+seed={2 if "seed2" in name else 1}']
 r=subprocess.run(args,capture_output=True,text=True);log=r.stdout+r.stderr;(a.out/(name+'.log')).write_text(log)
 summary=[s for s in log.splitlines() if s.startswith(('ATTN1_COMPLETE','ATTN1PROBE','ATTN1LOCK'))]
 passed=any(s.startswith('ATTN1LOCK') and s.endswith(' PASS') for s in summary)
 failed=any(s.startswith('ATTN1LOCK') and s.endswith(' FAIL') for s in summary)
 causal=any(s.startswith('ATTN1LOCK') and ('sc_mis=0 pv_mis=0' not in s) for s in summary)
 expected=(passed and a.mutant==0) or (failed and causal and a.mutant!=0)
 row=dict(name=name,command=args,exit=r.returncode,summary=summary,expected_outcome=expected,binary_sha256=sha)
 rows.append(row); print(json.dumps(row),flush=True)
(a.out/'summary.json').write_text(json.dumps(rows,indent=2)+'\n')
raise SystemExit(0 if all(r['expected_outcome'] for r in rows) else 1)
