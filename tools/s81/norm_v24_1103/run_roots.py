#!/usr/bin/env python3
"""Reproduce two-root equivalence and independent stopped-clock negatives."""
import json, pathlib, subprocess, sys
r=pathlib.Path(__file__).resolve().parents[3]
p=pathlib.Path(__file__).resolve().parent
out=pathlib.Path(sys.argv[1]).resolve();out.mkdir(parents=True,exist_ok=True)
s=json.loads((r/'physical/ref_tile/s81hc_ctfxsnt_ref/spec.json').read_text())
v=pathlib.Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator'
cmd=[str(v),'--binary','--timing','--build-jobs','4','-Wno-fatal','-Wno-lint','-Wno-style','-Wno-TIMESCALEMOD','-DSYNTHESIS','--top-module','tb_roots','--Mdir',str(out/'obj'),str(p/'reference_ctfx.sv'),str(p/'tb_roots.sv'),*s['sources']]
with (out/'build.log').open('w') as log:subprocess.run(cmd,cwd=r,stdout=log,stderr=subprocess.STDOUT,check=True)
for m in [0,1,2]:
 q=subprocess.run([str(out/'obj/Vtb_roots'),f'+MUT={m}'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
 (out/f'mut{m}.log').write_text(q.stdout)
 expected=(q.returncode==0 and 'ROOT_EXACT_PASS mutant=0 cycles=2048 normal_edges_added=0' in q.stdout) if m==0 else (q.returncode!=0 and f'ROOT_MISMATCH mutant={m} cycle=128' in q.stdout)
 if not expected:raise SystemExit(f'unexpected result for mutant{m}: {q.stdout}')
print('TWO_ROOT_PROOF_PASS exact2048 data_stop128 lane_stop128')
