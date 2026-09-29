#!/usr/bin/env python3
"""Run pinned, single-job full-geometry vectors on existing executable."""
import argparse,json,hashlib,re,subprocess,time
from pathlib import Path

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--exe',type=Path,required=True);p.add_argument('--vectors',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 m=json.loads((a.vectors/'manifest.json').read_text());results=[]
 for c in m['cases']:
  d=(a.vectors/c['name']).resolve()
  for n,h in c['images'].items():assert sha(d/n)==h
  before=time.monotonic();r=subprocess.run([str(a.exe.resolve()),f'+dir={d}','+njob=1','+seed=20260929'],capture_output=True,text=True,timeout=600)
  (a.out/(c['name']+'.log')).write_text(r.stdout+r.stderr)
  lines=[x for x in r.stdout.splitlines() if x.startswith('V41XATTN ')]
  fields={k:int(v) for k,v in re.findall(r'(\w+)=(-?\d+)',lines[-1])} if lines else {}
  passed=r.returncode==0 and fields.get('jobs')==1 and fields.get('faults')==c['expected']['score_faults']+c['expected']['pv_faults'] and fields.get('timeout')==0 and fields.get('sc_errors')==0 and fields.get('pv_errors')==0 and fields.get('sc_checked')==c['expected']['scores'] and fields.get('pv_checked')==c['expected']['pv']
  results.append(dict(name=c['name'],pass_=passed,returncode=r.returncode,fields=fields,wall_seconds=time.monotonic()-before))
 record=dict(scope=m['scope'],executable_sha256=sha(a.exe),manifest_sha256=sha(a.vectors/'manifest.json'),results=results,status='pass' if all(r['pass_'] for r in results) else 'fail')
 (a.out/'result.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record));raise SystemExit(0 if record['status']=='pass' else 1)
if __name__=='__main__':main()
