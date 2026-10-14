#!/usr/bin/env python3
"""Raw clock-stopped reset and individually captured ACK fixture gate."""
import argparse,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=Path);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 src=['rtl/dsrom_sys/s81_ph/relays/dsfd_die_relays.sv','rtl/dsrom_sys/s81_ph/test/tb_dsfd_be_fault_local_reset.sv'];cases=[]
 for name,define in [('positive',None),('mut_common_rn','OT_BE_FAULT_MUT_COMMON_RN'),('mut_pre_and_ack','OT_BE_ACK_MUT_PRE_AND')]:
  exe=a.out/(name+'.vvp');cmd=['iverilog','-g2012','-s','tb_dsfd_be_fault_local_reset','-o',str(exe)]+(['-D'+define] if define else [])+[str(ROOT/s) for s in src]
  b=subprocess.run(cmd,text=True,capture_output=True);(a.out/(name+'.build.log')).write_text(b.stdout+b.stderr)
  if b.returncode:raise RuntimeError('build failed '+name)
  r=subprocess.run(['vvp',str(exe)],text=True,capture_output=True);log=r.stdout+r.stderr;(a.out/(name+'.run.log')).write_text(log)
  ok=(r.returncode==0 and 'PASS LOCAL_RAW_RESET_AND_INDIVIDUAL_ACK' in log) if not define else (r.returncode!=0 and 'FAIL' in log and 'RESULT local_stages=10' in log)
  cases.append(dict(case=name,expect='fail' if define else 'pass',observed_exit=r.returncode,ok=ok,log_sha256=hashlib.sha256(log.encode()).hexdigest()))
 record=dict(source_sha256={s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in src},cases=cases,pass_=all(c['ok'] for c in cases),controller_clock='TEST_ONLY independent 14ns fixture',actual_controller_clock=None,actual_controller_reset_ports=None,actual_raw_reset_driver=None,physical_adopted=False);(a.out/'record.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record));return 0 if record['pass_'] else 1
if __name__=='__main__':raise SystemExit(main())
