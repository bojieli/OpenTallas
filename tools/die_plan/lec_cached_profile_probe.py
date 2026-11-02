"""Diagnostic full native LEC replay with cached, untrusted correspondence proposals.

All native input/reset/kept-register gates, induction, failing-hint dropping and compare
points run unchanged. Only stochastic proposal discovery is set to zero rounds;
finished hypotheses plus the explicit candidate are re-proved, never trusted.
Outputs are separate from the original failed capsule and require normal review.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path

p=argparse.ArgumentParser()
p.add_argument('--kit',required=True)
p.add_argument('--out',required=True)
p.add_argument('--hints',required=True)
a=p.parse_args()
kit,out=Path(a.kit),Path(a.out)
spec=importlib.util.spec_from_file_location('frozen_native_lec',kit/'lec.py')
e=importlib.util.module_from_spec(spec);spec.loader.exec_module(e)
native=e.correspond

def cached_candidates(L,work,conflicts,log,**kwargs):
    log.append('CACHED PROFILE PROBE: zero stochastic candidate-discovery rounds; native induction and all compare gates retained')
    return native(L,work,conflicts,log,rounds=0,sim_iters=0)

e.correspond=cached_candidates
e.PROVE_JOBS=2
os.environ['OT_LEC_HINTS_PRESEED']='1'
r=e.check(str(kit),out=str(out),reuse=True,hints=a.hints)
r['cached_profile_probe']=dict(discovery_rounds=0,untrusted_hints=str(a.hints),
    native_engine_sha256=hashlib.sha256((kit/'lec.py').read_bytes()).hexdigest(),
    driver_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    source='same frozen source/netlist/AIG capsule; every proposal and compare re-proved',
    baseline_verdict='NOT EQUIVALENT retained in original capsule')
(out/'lec.json').write_text(json.dumps(r,indent=1)+'\n')
print('NATIVE_PROFILE_PROBE',r['verdict'],r.get('counts'),r.get('reason',''),flush=True)
raise SystemExit({'EQUIVALENT':0,'NOT EQUIVALENT':1}.get(r['verdict'],2))
