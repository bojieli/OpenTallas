#!/usr/bin/env python3
"""Verify completed native32 workload against committed baseline trace identity."""
import argparse,hashlib,json,re
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('work',type=Path);p.add_argument('positive');p.add_argument('mutants',nargs='+');a=p.parse_args()
expected='c6cf9839168a375a834868cafa63e42973d5c49e8f3f203b1c8d25d8f495bf0d'
t=json.loads((a.work/'terminal.json').read_text());assert t['cases'][a.positive]['ok'],t
trace=(a.work/a.positive/'candidate_edges.txt').read_bytes();digest=hashlib.sha256(trace).hexdigest();assert digest==expected,(digest,expected)
assert len(trace.splitlines())==124422
m={}
for n in a.mutants:
 r=t['cases'][n];log=(a.work/n/'run.log').read_text();assert r['ok'] and re.search(r'DIFF TXN lane=',log),(n,r,log[-1000:])
 mt=(a.work/n/'candidate_edges.txt').read_bytes();mh=hashlib.sha256(mt).hexdigest();assert mh!=digest,n
 first=next((i for i,(x,y) in enumerate(zip(trace.splitlines(),mt.splitlines()),1) if x!=y),None)
 if first is None and len(mt.splitlines()) != len(trace.splitlines()):first=min(len(mt.splitlines()),len(trace.splitlines()))+1
 m[n]={'returncode':r['returncode'],'first_trace_mismatch':first,'sha256':mh,'fail_regex':'DIFF TXN lane='}
r={'status':'PASS','positive':a.positive,'trace_sha256':digest,'trace_lines':124422,'extra_data_edges':0,'mutants':m,'baseline_record':'results/rtl/s81_c199_freeclk_1019/forep/forep_exact.json @4496f1308'}
(a.work/'native32_exact.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True)
