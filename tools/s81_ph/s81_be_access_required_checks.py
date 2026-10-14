#!/usr/bin/env python3
"""Bind reused native proof and all effective helpers before diagnostic launch."""
import argparse,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/closure_loop'))
import helper_overlay as HO

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--cl',type=Path);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    kit=ROOT/'physical/s81_be_access_m7_candidate'
    proof=json.loads((kit/'exact_gate_binding.json').read_text());checks={}
    for rel,expected in proof['source_sha256'].items():
        p=ROOT/rel;checks[rel]=dict(expected=expected,actual=sha(p),pass_=sha(p)==expected)
    if not all(v['pass_'] for v in checks.values()):raise SystemExit('NATIVE_PROOF_SOURCE_MISMATCH')
    assert any(c['case']=='be-native-gold_s1' and c['passes_expected'] for c in proof['cases'])
    assert any(c['case']=='be-native-tp' and c['passes_expected'] for c in proof['cases'])
    assert any(c['case']=='be-native-mut_stale' and c['passes_expected'] for c in proof['cases'])
    frozen=json.loads((kit/'helper_overlay_plan.json').read_text())
    actual=frozen if a.cl is None else json.loads((a.cl/'helper_overlay_plan.json').read_text())
    ok,why=HO.compare_plans(frozen,actual)
    if not ok:raise SystemExit('HELPER_DRIFT: '+why)
    assert len(actual['files'])==46
    applied=[]
    if a.cl:
        # Copy the exact admitted helper payloads into the job's isolated source
        # snapshot; no global/FH snapshots or published views are changed here.
        for f in actual['files']:
            src=a.cl/Path(f['path']).name
            if sha(src)!=f['sha256']:raise SystemExit('SHIPPED_HELPER_HASH_MISMATCH '+f['path'])
            target=ROOT/f['path'];target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(src.read_bytes());target.chmod(f['mode']);applied.append(f['path'])
    record=dict(schema='opentallas.be_access_required_checks.v1',native_proof='SOURCE_HASH_MATCH_REUSE',reused_not_rerun=True,
                sources=checks,helper_plan_sha256=actual['content_sha256'],helper_count=len(actual['files']),applied_helpers=applied,
                helper_identity='exact_content_snapshot',candidate_view_cap='M7',global_clocks_and_reset_refs_bound=False,
                slot_allocated=False,diagnostic_only=True,checks_pass=True)
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(record,indent=2)+'\n');print('BE_ACCESS_REQUIRED_CHECKS_PASS')
if __name__=='__main__':main()
