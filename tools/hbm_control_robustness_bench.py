"""Minimum integrated reset, fault and stalled token-loop gate; preserves failures."""
import argparse,hashlib,json,pathlib,subprocess
ROOT=pathlib.Path(__file__).resolve().parents[1]
SOURCES=['rtl/hbm_accel/control/ot_hbm_reset_seq.sv','rtl/hbm_accel/control/ot_hbm_fault_agg.sv','rtl/hbm_accel/control/ot_hbm_token_loop.sv','rtl/test/hbm_accel/tb_hbm_control_robustness.sv']
def main():
 p=argparse.ArgumentParser();p.add_argument('--work',type=pathlib.Path,required=True);p.add_argument('--out',type=pathlib.Path,required=True);a=p.parse_args()
 if a.out.exists():raise SystemExit('fresh evidence path required')
 a.work.mkdir(parents=True,exist_ok=True);cases=[]
 for mutant in ('none','fault_disconnected','reset_before_bist'):
  src=[ROOT/x for x in SOURCES]
  if mutant=='fault_disconnected':
   q=a.work/'fault_disconnected.sv';q.write_text(src[-1].read_text().replace('.external_fault(fault)',".external_fault(1'b0)"));src[-1]=q
  elif mutant=='reset_before_bist':
   q=a.work/'reset_before_bist.sv';q.write_text(src[0].read_text().replace('assign cmd_reset_n=por_n && state==RUN;','assign cmd_reset_n=por_n && (state==BIST || state==RUN);'));src[0]=q
  exe=a.work/(mutant+'.vvp');b=subprocess.run(['iverilog','-g2012','-s','tb_hbm_control_robustness','-o',str(exe),*map(str,src)],capture_output=True,text=True)
  if b.returncode:raise RuntimeError(b.stderr)
  r=subprocess.run(['vvp',str(exe)],capture_output=True,text=True);cases.append(dict(case=mutant,returncode=r.returncode,output=r.stdout.strip(),verdict='PASS' if r.returncode==0 else 'FAIL'))
 ok=cases[0]['verdict']=='PASS' and all(c['verdict']=='FAIL' for c in cases[1:])
 record=dict(schema='opentallas.hbm_control_robustness.rtl.v1',verdict='PASS' if ok else 'FAIL',scope='minimum integrated control components; no physical or die-wiring signoff',input_sha256={s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in SOURCES+['tools/hbm_control_robustness_bench.py','tools/hbm_control_robustness_model.py']},cases=cases,limitations=['Per-region asynchronous event transport and die wiring are not qualified','SS/FF routes pending','Other production SRAMs still need SECDED integration'])
 a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2));raise SystemExit(0 if ok else 1)
if __name__=='__main__':main()
