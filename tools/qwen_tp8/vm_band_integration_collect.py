#!/usr/bin/env python3
"""Collect copied integration logs; refuses missing/mismatched final proof."""
import hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'results/rtl/qwen_tp8_vm_plane_20261013/vm_band_integration'

def main():
 manifest=json.loads((OUT/'submissions_codex.json').read_text());rows=[];complete=True
 for p,h in manifest['source_sha256'].items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h,('source changed',p)
 for job in manifest['jobs']:
  log=OUT/job['mode']/'run.log';positive=job['mode']in ('native','fallback')
  text=log.read_text()if log.exists()else''
  match=re.search(r'^PASS integration SMAX=(\d+) MUT=(\d+).*lane_checks=(\d+) checks=(\d+) valids=(\d+) stalls=(\d+)',text,re.M)
  failure=re.search(r'^FAIL integration SMAX=(\d+) MUT=(\d+) errors=(\d+) checks=(\d+) lane_checks=(\d+)',text,re.M)
  good=bool(match) if positive else bool(failure)
  expected_sm=9 if job['mode'].startswith('native') else 11
  expected_mut=0 if positive else 1 if job['mode'].endswith('_delay') else 2
  verdict=match if positive else failure
  if verdict:
   assert int(verdict[1])==expected_sm and int(verdict[2])==expected_mut
  if failure:
   assert int(failure[3])>0 and int(failure[4])==(4000-41)*32 and int(failure[5])==(4000-41)*4096
  if match:
   assert int(match[3])==(4000-41)*4096 and int(match[4])==(4000-41)*32
  good = good and job.get('otrun_exit') == 0
  complete &= good
  rows.append(dict(**job,run_log=str(log.relative_to(ROOT)),expected='PASS'if positive else'FAIL',observed='PASS'if match else'FAIL'if 'FAIL integration 'in text else'MISSING',gate_evidence=good,metrics=match.groups()if match else None))
 rec=dict(schema='opentallas.qwen.vm-band-integration-proof.v1',status='TRUE_FULLFAN_REALBAND_FUNCTIONAL_PASS_PHYSICAL_UNQUALIFIED'if complete else'INCOMPLETE',source_sha256=manifest['source_sha256'],runs=rows,
 scope='Actual116fan control/ME composition plus actual32xcol_roots and270padtiles/4096lanes; independent behavioral PC/LC/tag3enabled-stage reference andME2free-stage reference; sourcebankorder computed fromlaneidentity; separate32xplane/xline plus3edge taggedroot references. Outputdata/phases/epochs/valid compared everyclock afterwarmup, includinginvalid outputs.',
 physical_assignment='UNASSIGNED; threelevel logicalfan topology is not a fullband500um placement claim',root_gather='Separate gather proof; not instantiated by this gate',production_throughput='UNMEASURED',production_price='UNMEASURED',qualification=False)
 (OUT/'record.json').write_text(json.dumps(rec,indent=2)+'\n');print(rec['status']);return 0 if complete else 1
if __name__=='__main__':raise SystemExit(main())
