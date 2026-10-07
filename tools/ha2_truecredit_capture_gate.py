#!/usr/bin/env python3
"""Targeted full-width original/candidate lockstep and invalid payload activity."""
import argparse,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
FILES=['rtl/hbm_accel/ha2_ar/'+n+'.sv' for n in ['ot_ha2_prims','ot_ha2_parent_quiet_prims','ot_ha2_truecredit','ot_ha2_truecredit_sender_capture','ot_ha2_hub_launch_single','tb_ha2_truecredit_capture']]
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=Path);a=p.parse_args();o=a.out.resolve();o.mkdir(parents=True,exist_ok=False);checks={}
 for delay in [7,64]:
  name=f'f{delay}_r{delay}';exe=o/(name+'.vvp');cmd=['iverilog','-g2012','-s','tb_ha2_truecredit_capture',f'-Ptb_ha2_truecredit_capture.FWD={delay}',f'-Ptb_ha2_truecredit_capture.RET={delay}','-o',str(exe),*FILES]
  b=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True);(o/(name+'.compile.log')).write_text(b.stdout+b.stderr)
  if b.returncode:raise RuntimeError('Compile failure')
  r=subprocess.run(['vvp',str(exe)],capture_output=True,text=True);t=r.stdout+r.stderr;(o/(name+'.log')).write_text(t);checks[name]=dict(passed=r.returncode==0 and 'PASS_TRUECREDIT' in t and 'CAPTURE_ACTIVITY' in t,output=t);print(name,t.strip(),flush=True)
 reset_file='rtl/hbm_accel/ha2_ar/tb_ha2_hub_split_reset.sv'
 exe=o/'split_reset.vvp';b=subprocess.run(['iverilog','-g2012','-s','tb_ha2_hub_split_reset','-o',str(exe),*FILES,reset_file],cwd=ROOT,capture_output=True,text=True);(o/'split_reset.compile.log').write_text(b.stdout+b.stderr)
 if b.returncode:raise RuntimeError('Reset compile failure')
 r=subprocess.run(['vvp',str(exe)],capture_output=True,text=True);t=r.stdout+r.stderr;(o/'split_reset.log').write_text(t);checks['split_reset']=dict(passed=r.returncode==0 and 'PASS_SPLIT_RESET' in t,output=t);print(t.strip())
 record=dict(passed=all(c['passed'] for c in checks.values()),checks=checks,source_sha256={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in [*FILES,reset_file,'tools/ha2_truecredit_capture_gate.py']},scope='2x544bit valid-data equivalence and exact controls/tags/credit timing under stalls and poisoned invalid payload. D35 ring vs D34+D1 split. No parent physical timing claim.',switching_energy='Alternating invalid input poison is stress activity, not workload power. Register output bit-transition counts are measured activity only. Extra dynamic energy=sum(extra toggles_i*C_i*V^2/2); actual cell/net capacitance and voltage required; enable mux removal offsets unmeasured. No absolute power claim.')
 (o/'terminal.json').write_text(json.dumps(record,indent=2)+'\n');return 0 if record['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
