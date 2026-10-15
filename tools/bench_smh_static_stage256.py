#!/usr/bin/env python3
"""Minimum actual256-bit clock-root stage proof against original SM RTL."""
import argparse,base64,gzip,hashlib,io,json,re,shlex,subprocess,tarfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sources=['rtl/hbm_accel/sm/static/ot_smh_static_stage256.sv','rtl/test/tb_smh_static_stage256.sv','rtl/hbm_accel/sm/ot_hbm_accel_smh.sv']
p=argparse.ArgumentParser();p.add_argument('--out',required=True);p.add_argument('--worker',action='store_true');p.add_argument('--case',choices=['both','normal','mutant'],default='both');a=p.parse_args()
if not a.worker:
 stream=io.BytesIO()
 with tarfile.open(fileobj=stream,mode='w') as t:
  for f in sources+['tools/bench_smh_static_stage256.py']:
   b=(ROOT/f).read_bytes();n=tarfile.TarInfo(f);n.size=len(b);t.addfile(n,io.BytesIO(b))
 payload=base64.b64encode(gzip.compress(stream.getvalue())).decode()
 script=f'''set -e
work=$(mktemp -d /var/tmp/smh-stage256-src.XXXXXX)
cd "$work"
printf '%s' '{payload}' | base64 -d | gzip -dc | tar xf -
python3 tools/bench_smh_static_stage256.py --worker --case {a.case} --out {shlex.quote(a.out)}
'''
 raise SystemExit(subprocess.call(['/home/ubuntu/bin/ot-run','--mem','2','--threads','1','--','bash','-c',script]))
out=Path(a.out);out.mkdir(parents=True,exist_ok=False)
original=(ROOT/sources[2]).read_text();ref=re.search(r'\bmodule ot_hbm_accel_smh_kreg\b.*?\bendmodule',original,re.S).group()
(out/'original.sv').write_text(ref)
report={'scope':'one actual256-bit onecaptureedge clock-root stage only; no32SM throughput/fit qualification','source_sha256':{s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in sources},'cases':[]}
for mut in ((0,1) if a.case=='both' else ((1,) if a.case=='mutant' else (0,))):
 d=out/str(mut);d.mkdir();exe=d/'bench'
 build=subprocess.run(['iverilog','-g2012','-s','tb_smh_static_stage256',f'-Ptb_smh_static_stage256.MUT={mut}','-o',str(exe)]+[str(ROOT/s) for s in sources[:2]]+[str(out/'original.sv')],capture_output=True,text=True)
 (d/'build.log').write_text(build.stdout+build.stderr);assert build.returncode==0,build.stderr
 run=subprocess.run(['vvp',str(exe)],capture_output=True,text=True)
 (d/'run.log').write_text(run.stdout+run.stderr)
 if a.case=='mutant':
  print(run.stdout+run.stderr);raise SystemExit(run.returncode)
 report['cases'].append({'mutant':mut,'returncode':run.returncode,'expected_pass':mut==0})
 assert (run.returncode==0)==(mut==0),run.stdout+run.stderr
report['verdict']='PASS';(out/'verdict.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
