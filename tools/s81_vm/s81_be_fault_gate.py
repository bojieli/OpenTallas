#!/usr/bin/env python3
"""Source-pinned status transport waveform gate; observed mutants must fail."""
import argparse,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
 src=['rtl/dsrom_sys/s81_ph/relays/dsfd_die_relays.sv','rtl/dsrom_sys/s81_ph/test/tb_dsfd_be_fault_path.sv'];results=[]
 for name,define in [('positive',None),('mut_bypass','OT_BE_FAULT_MUT_BYPASS'),('mut_wrong_stage','OT_BE_FAULT_MUT_WRONG_STAGE')]:
  exe=out/(name+'.vvp');cmd=['iverilog','-g2012','-s','tb_dsfd_be_fault_path','-o',str(exe)]+(['-D'+define] if define else [])+[str(ROOT/s) for s in src]
  b=subprocess.run(cmd,text=True,capture_output=True);(out/(name+'.build.log')).write_text(b.stdout+b.stderr)
  if b.returncode: raise RuntimeError('build failed '+name)
  r=subprocess.run(['vvp',str(exe)],text=True,capture_output=True);log=r.stdout+r.stderr;(out/(name+'.run.log')).write_text(log)
  ok=(r.returncode==0 and 'PASS FAULT_PATH_EXACT_LATENCY_RESET' in log) if not define else (r.returncode!=0 and 'FAIL waveform' in log and 'RESULT checks=160' in log)
  results.append(dict(case=name,expected='fail' if define else 'pass',observed_exit=r.returncode,ok=ok,log_sha256=hashlib.sha256(log.encode()).hexdigest()))
 record=dict(source_sha256={s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in src},cases=results,pass_=all(r['ok'] for r in results));(out/'record.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record));return 0 if record['pass_'] else 1
if __name__=='__main__':raise SystemExit(main())
