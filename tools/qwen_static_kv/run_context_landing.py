#!/usr/bin/env python3
"""Existing native landing numerical/timing golden plus actual pipeline idle observation."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser();p.add_argument('out',type=Path);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
subprocess.run([sys.executable,str(ROOT/'tools/qwen_static_kv/landing_cal_golden.py'),str(a.out/'cases')],check=True)
files=['rtl/qwen_sys/static_kv_20261014/qkd_kv_context_landing_cal.sv','rtl/test/qwen_static_kv/tb_qkd_kv_context_landing_cal.sv'];results=[]
for case in sorted((a.out/'cases').glob('*.txt')):
 phase=int(case.read_text().splitlines()[0].split()[3]);binary=a.out/f'sim_p{phase}'
 if not binary.exists():subprocess.run(['iverilog','-g2012','-s','tb_qkd_kv_context_landing_cal',f'-Ptb_qkd_kv_context_landing_cal.PH0={phase}','-o',str(binary)]+[str(ROOT/f)for f in files],check=True,capture_output=True)
 r=subprocess.run(['vvp',str(binary),f'+CASE={case}'],capture_output=True,text=True);results.append(dict(case=case.name,exit=r.returncode,output=r.stdout))
 if r.returncode or 'PASS landing_cal'not in r.stdout:break
okay=len(results)==len(list((a.out/'cases').glob('*.txt'))) and all(r['exit']==0 and 'PASS landing_cal'in r['output']for r in results)
rec=dict(passed=okay,cases=len(results),results=results,source_sha256={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest()for f in files},scope='actual landing calendar and registered idle; source golden consumer schedule, not physical/native-die qualification')
(a.out/'receipt.json').write_text(json.dumps(rec,indent=2)+'\n');print(json.dumps(dict(passed=okay,cases=len(results))));raise SystemExit(0 if okay else 1)
