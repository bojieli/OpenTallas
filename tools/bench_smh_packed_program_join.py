#!/usr/bin/env python3
"""Actual SRAM83-bit programme calendar gate, independent of SM arithmetic."""
import argparse,base64,gzip,hashlib,io,json,shlex,subprocess,tarfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sources=['rtl/hbm_accel/sm/static/ot_smh_calendar_static.sv','rtl/test/tb_smh_packed_program_join.sv','physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v','rtl/hbm_accel/sm/static/ot_smh_packed_program_join.sv','rtl/hbm_accel/sm/static/ot_smh_static_feed.sv','rtl/hbm_accel/loader/service_native/ot_hbm_svc_static_sm_packed136.sv','physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v']
p=argparse.ArgumentParser();p.add_argument('--out',required=True);p.add_argument('--worker',action='store_true');a=p.parse_args()
if not a.worker:
 stream=io.BytesIO()
 with tarfile.open(fileobj=stream,mode='w') as t:
  for f in sources+['tools/bench_smh_packed_program_join.py']:
   b=(ROOT/f).read_bytes();n=tarfile.TarInfo(f);n.size=len(b);t.addfile(n,io.BytesIO(b))
 payload=base64.b64encode(gzip.compress(stream.getvalue())).decode()
 script=f'''set -e
work=$(mktemp -d /var/tmp/smh-calendar-src.XXXXXX)
cd "$work"
printf '%s' '{payload}' | base64 -d | gzip -dc | tar xf -
python3 tools/bench_smh_packed_program_join.py --worker --out {shlex.quote(a.out)}
'''
 raise SystemExit(subprocess.call(['/home/ubuntu/bin/ot-run','--mem','2','--threads','1','--','bash','-c',script]))
out=Path(a.out);out.mkdir(parents=True,exist_ok=False)
report={'scope':'actual2programmeSRAM+5cacheSRAM packed136 static programme/feed join; proceduralsourceboundary only, not releasedcheckpoint/4PCWB/34band/nativeSMnumerical qualification','source_sha256':{s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in sources},'cases':[]}
for mut in (0,1):
 d=out/str(mut);d.mkdir();exe=d/'bench'
 build=subprocess.run(['iverilog','-g2012','-s','tb_smh_packed_program_join',f'-Ptb_smh_packed_program_join.MUT={mut}','-o',str(exe)]+[str(ROOT/s) for s in sources],capture_output=True,text=True)
 (d/'build.log').write_text(build.stdout+build.stderr);assert build.returncode==0,build.stderr
 run=subprocess.run(['vvp',str(exe)],capture_output=True,text=True)
 (d/'run.log').write_text(run.stdout+run.stderr)
 report['cases'].append({'mutant':mut,'returncode':run.returncode,'expected_pass':mut==0})
 assert (run.returncode==0)==(mut==0),run.stdout+run.stderr
report['verdict']='PASS';(out/'verdict.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
