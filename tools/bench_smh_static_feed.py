#!/usr/bin/env python3
"""Smallest production-width feed gate. Run through ot-run; no whole-SM build."""
import argparse,hashlib,json,subprocess,tempfile,base64,gzip,tarfile,io,shlex,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--out',required=True);p.add_argument('--worker',action='store_true');a=p.parse_args()
sources=['rtl/hbm_accel/sm/static/ot_smh_static_feed.sv','rtl/test/tb_smh_static_feed.sv','rtl/hbm_accel/sm/ot_hbm_accel_smh.sv']
if not a.worker:
 stream=io.BytesIO()
 with tarfile.open(fileobj=stream,mode='w') as t:
  for f in sources+['tools/bench_smh_static_feed.py']:
   b=(ROOT/f).read_bytes();n=tarfile.TarInfo(f);n.size=len(b);t.addfile(n,io.BytesIO(b))
 payload=base64.b64encode(gzip.compress(stream.getvalue())).decode()
 script=f'''set -e
work=$(mktemp -d /var/tmp/smh-feed-src.XXXXXX)
cd "$work"
printf '%s' '{payload}' | base64 -d | gzip -dc | tar xf -
python3 tools/bench_smh_static_feed.py --worker --out {shlex.quote(a.out)}
'''
 raise SystemExit(subprocess.call(['/home/ubuntu/bin/ot-run','--mem','2','--threads','1','--','bash','-c',script]))
out=Path(a.out);out.mkdir(parents=True,exist_ok=False)
original=(ROOT/'rtl/hbm_accel/sm/ot_hbm_accel_smh.sv').read_text()
body=re.search(r'\bmodule ot_hbm_accel_smh_fc_is\b.*?\bendmodule',original,re.S).group()
s1=body[body.index('    reg [1087:0]     s1_w;'):body.rindex('endmodule')]
fmt=body[body.index('    // format launch copies'):body.index('`ifdef OT_SMH_MUT_BFDLY')]
kreg=re.search(r'\bmodule ot_hbm_accel_smh_kreg\b.*?\bendmodule',original,re.S).group()
reference="""`timescale 1ns/1ps
module smh_original_s1_reference(input wire clk,rst_n,input wire [82:0] command,
 input wire [1098:0] packet,output wire [1081:0] lt0,lt1,output wire [569:0] lb0,lb1,output wire [11:0] fm);
 localparam integer RW=12,TAGW=16,XW=7,S1W=26;
 wire rn=rst_n;
 wire adv=command[25],row_ok=1'b1,i_first=command[24],i_last=command[23],i_glast=command[10];
 wire [12:0] row_now={1'b0,command[22:11]};wire [2:0] si=command[9:7];
 wire [6:0] xa=command[6:0],xb_q=0;
 wire [1087:0] issue_w_data=packet[1087:0];
 wire pop_r=command[28];wire [1:0] fmt_q=command[27:26];
"""+fmt+s1+'\nendmodule\n'+kreg
(out/'original_reference.sv').write_text(reference)
report={'scope':'production-width static feed component only; no arithmetic/die qualification',
 'source_sha256':{s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in sources},'cases':[]}
for mut in (0,1):
 d=out/str(mut);d.mkdir();exe=d/'bench'
 build=subprocess.run(['iverilog','-g2012','-s','tb_smh_static_feed',f'-Ptb_smh_static_feed.MUT={mut}','-o',str(exe)]+[str(ROOT/s) for s in sources[:2]]+[str(out/'original_reference.sv')],capture_output=True,text=True)
 (d/'build.log').write_text(build.stdout+build.stderr)
 assert build.returncode==0,build.stderr
 run=subprocess.run(['vvp',str(exe)],capture_output=True,text=True)
 (d/'run.log').write_text(run.stdout+run.stderr)
 passed=run.returncode==0
 report['cases'].append({'mutant':mut,'returncode':run.returncode,'expected_pass':mut==0})
 assert passed==(mut==0),run.stdout+run.stderr
report['verdict']='PASS';(out/'verdict.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
