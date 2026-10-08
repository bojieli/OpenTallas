#!/usr/bin/env python3
"""Minimum actual full-lane GSH stage gate; arithmetic campaigns remain separate."""
import argparse,hashlib,json,subprocess,tempfile
from pathlib import Path
R=Path(__file__).resolve().parents[1]
def main(out):
 out.mkdir(parents=True,exist_ok=True)
 sources=(R/'physical/hbm_su_div64/su_full_gsh1_sources.txt').read_text().splitlines()+['rtl/test/tb_hbm_su_gsh1_metadata.sv']
 verdict={}
 with tempfile.TemporaryDirectory(prefix='hbm-gsh1-') as t:
  t=Path(t)
  for case in ['positive','cpair_misalignment_negative']:
   paths=[R/x for x in sources]
   if case!='positive':
    original=R/'rtl/hbm_accel/su/div64_candidate/ot_hdc_v41x_vec_lane_c12.sv'
    txt=original.read_text();assert txt.count('s_cpair <= q_cpair;')==1
    mutant=t/'mutant.sv';mutant.write_text(txt.replace('s_cpair <= q_cpair;','s_cpair <= ~q_cpair;'))
    paths=[mutant if x==original else x for x in paths]
   exe=t/case
   p=subprocess.run(['iverilog','-g2012','-s','tb','-o',str(exe),*map(str,paths)],capture_output=True,text=True,cwd=R)
   (out/(case+'.compile.log')).write_text(p.stdout+p.stderr);p.check_returncode()
   p=subprocess.run(['vvp',str(exe)],capture_output=True,text=True,cwd=R)
   (out/(case+'.runtime.log')).write_text(p.stdout+p.stderr)
   verdict[case]=dict(exit=p.returncode,expected_pass=case=='positive',pass_=p.returncode==0 if case=='positive' else p.returncode!=0 and 'GSH_METADATA' in p.stdout)
 assert all(x['pass_'] for x in verdict.values()),verdict
 record=dict(schema='opentallas.hbm_su.gsh1_metadata_gate.v1',cases=verdict,
  scope='Actual full64 successor GSH stage and following read-address association. Stimulated internal gather registers isolate mechanism; full scheduled arithmetic random/vehicle campaign still required.',
  vectors=384,shift_values=32,all_h_metadata_checked=True,reset_valid_checked=True,
  sources={x:hashlib.sha256((R/x).read_bytes()).hexdigest() for x in sources})
 (out/'summary.json').write_text(json.dumps(record,indent=2)+'\n')
 print(json.dumps(verdict))
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();main(a.out)
