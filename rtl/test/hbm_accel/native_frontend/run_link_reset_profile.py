#!/usr/bin/env python3
import argparse,hashlib,json,pathlib,subprocess
p=argparse.ArgumentParser();p.add_argument('output');p.add_argument('--mutant',choices=['none','early','late'],default='none');a=p.parse_args();out=pathlib.Path(a.output).resolve();out.mkdir(parents=True,exist_ok=True)
source=pathlib.Path('rtl/hbm_accel/loader/service_native/ot_hbm_svc_four_owner_links.sv');s=source.read_text();original=hashlib.sha256(source.read_bytes()).hexdigest()
needle='(* keep = "yes" *) reg reset_q;\n always @(posedge clk or negedge first_rst_n)\n  if(!first_rst_n)reset_q<=0;else reset_q<=1;'
if a.mutant=='early':
 assert needle in s;s=s.replace(needle,'wire reset_q=first_rst_n;')
if a.mutant=='late':
 assert needle in s;s=s.replace(needle,'reg mid_q;always @(posedge clk or negedge first_rst_n)if(!first_rst_n)mid_q<=0;else mid_q<=1;\n reg reset_q;always @(posedge clk or negedge mid_q)if(!mid_q)reset_q<=0;else reset_q<=1;')
rtl=out/'source.sv';rtl.write_text(s);vlt=pathlib.Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator'
(out/'source_identity.json').write_text(json.dumps(dict(original_sha256=original,variant_sha256=hashlib.sha256(s.encode()).hexdigest(),mutant=a.mutant),indent=2))
with(out/'build.log').open('w')as f:r=subprocess.run([str(vlt),'--binary','--timing','-j','2','-Wno-fatal','--top-module','tb_link_reset_profile','--Mdir',str(out/'obj'),str(rtl),'rtl/test/hbm_accel/native_frontend/tb_link_reset_profile.sv'],stdout=f,stderr=subprocess.STDOUT)
if r.returncode:raise SystemExit(r.returncode)
raise SystemExit(subprocess.run([str(out/'obj/Vtb_link_reset_profile')]).returncode)
