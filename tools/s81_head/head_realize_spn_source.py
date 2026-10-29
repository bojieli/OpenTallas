#!/usr/bin/env python3
"""Realize existing HEAD plan internal stations in a fresh SOURCE7 copy.

Uses the shared kit_istations implementation before logical bind and physical
kit creation. Only hd_spn/hd_spn_end have such stations in the current plan.
The plan already prices them; this adds no new planned latency.
"""
import argparse,hashlib,json,shutil,sys
from pathlib import Path

def realize(repo,source,out):
 repo,source,out=map(Path,(repo,source,out))
 if out.exists():raise ValueError('fresh source output required')
 shutil.copytree(source,out,symlinks=False)
 sys.path.insert(0,str(repo/'tools/die_plan'))
 import kit_istations
 plan_path=out/'source_plan.json';p=json.load(open(plan_path));report={}
 for tn,t in p['partition_types'].items():
  if not t.get('internal_stations'):continue
  if tn not in ('hd_spn','hd_spn_end'):raise ValueError('unexpected new internal-station type: '+tn)
  module=t['module'];wrapper=out/(module+'.sv');before=wrapper.read_bytes()
  work=out/'station_realization'/tn;work.mkdir(parents=True)
  local=work/wrapper.name;local.write_bytes(before)
  (work/'kit_rtl.json').write_text(json.dumps(dict(files=[str(local.resolve())],bound_module=module)))
  kit_istations.main([str(plan_path.resolve()),tn,str(work.resolve()),'--apply'])
  wrapper.write_bytes(local.read_bytes())
  report[tn]=dict(before_sha256=hashlib.sha256(before).hexdigest(),after_sha256=hashlib.sha256(wrapper.read_bytes()).hexdigest(),
   stations=json.load(open(work/'kit_rtl.json'))['kit_istations'],new_planned_cycles=0)
 (out/'internal_station_realization.json').write_text(json.dumps(report,indent=1)+'\n')
 print(json.dumps({n:r['stations'] for n,r in report.items()}))
 return report

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('repo');ap.add_argument('source');ap.add_argument('out');a=ap.parse_args();realize(a.repo,a.source,a.out)
