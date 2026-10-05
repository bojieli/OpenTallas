"""Strict independent verification of raw frozen component and mutant receipts."""
import argparse,gzip,hashlib,json,re
from pathlib import Path
import ds_mtp_accept_rtl_preparation as P
ROOT=P.ROOT
MARKERS={**{c:f'FAULT_PASS record={c} 'for c in range(24)},**{c:f'CALLER_FAULT_PASS record={c-24}'for c in range(24,28)},
28:'FRESHNESS_PASS',29:'ACK_REFUSAL_PASS',30:'REARM_REFUSAL_PASS',31:'SINGLE72_PASS',32:'PRODUCER_STALE_PASS',33:'DUPLICATE_PASS',34:'START_BOUNDS_PASS',35:'BUSY_ORIGIN_PASS',36:'TERMINAL_BOUNDS_PASS',37:'CALLER_SINGLE72_PASS',38:'PADDING_PASS',39:'JOINT_FAULT_PASS',40:'FENCE_REFUSAL_PASS',41:'DEFAULT_OFF_PASS'}
def verify(path):
 r=json.loads((path/'record.json').read_text())
 assert r['source_commit']=='58bfa6afaf487c0b303dfa1452031f188b331722'
 assert r['source_hashes']==P.model()['source_hashes']
 for p,h in r['source_hashes'].items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h,p
 assert r['lint']['rc']==0 and r['compile']['rc']==0
 assert '%Warning'not in (path/'lint.log').read_text()and '%Error'not in(path/'lint.log').read_text()
 assert hashlib.sha256(gzip.decompress((path/'sim.vvp.gz').read_bytes())).hexdigest()==r['binary_sha256']
 assert [c['case']for c in r['cases']]==[-1,*range(42)]
 for c in r['cases']:
  text=(path/c['log']).read_text();assert c['rc']==0 and c['pass']and 'GATE_FAIL'not in text
  if c['case']==-1:
   got=[tuple(map(int,m))for m in re.findall(r'^PREFIX_PASS g=(\d+) a=(\d+)$',text,re.M)]
   assert got==[(g,a)for g in range(8)for a in range(g+1)]
   assert 'COMPONENT_PASS cycles=2709 cohorts=40'in text
  else:assert MARKERS[c['case']]in text,(c['case'],text)
 assert r['mutant_compile']['rc']==0 and r['mutant_run']['rc']!=0
 text=(path/'mutant_runtime.log').read_text();assert 'GATE_FAIL case=-1 cycles=42 literal source golden every active21-bit slot'in text
 assert r['mutant_detected_by_behavior']and r['pass']
 assert r['extra_stage']==0
 return dict(status='PASS_COMPONENT_PROTECTED_FUNCTIONAL_ONLY',directed_runs=43,prefix_cases=36,continuous_cohorts=40,
 positive_cycles=2709,leaf_double_fault_records=24,caller_double_fault_records=4,leaf_and_caller_single_bit_positions_each=72,
 mutant_detected_by_actual_behavior=True,source_commit=r['source_commit'],binary_sha256=r['binary_sha256'],
 strict_markers_verified=True,full_MTP=False,source_native_caller=False,physical_SS_FF=False,rate_qualified=False)
def main():
 p=argparse.ArgumentParser();p.add_argument('--path',type=Path,default=P.OUT/'runtime_r1');p.add_argument('--out',type=Path);a=p.parse_args();r=verify(a.path)
 b=json.dumps(r,indent=2,sort_keys=True)+'\n'
 if a.out:a.out.write_text(b)
 else:print(b,end='')
if __name__=='__main__':main()
