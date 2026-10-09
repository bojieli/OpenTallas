#!/usr/bin/env python3
"""Actual IKS service, timed REFpb controller, exact bytes and final credits.
Run on an admitted remote host, never a shared checkout. Retain all raw logs.
"""
import argparse, hashlib, json, os, re, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SRC=['rtl/hbm_accel/service/ot_hbm_accel_cdc_fifo.sv','rtl/hbm_accel/service/ot_hbm_kport_map.sv',
'physical/hbm_accel_die_views/svc/rtl/ot_hbm_index_lines.sv','physical/hbm_accel_die_views/svc/rtl/ot_hbm_svc_core.sv',
'rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv','rtl/test/hbm_accel/tb_hbm_svc_iks_binding.sv']
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--work',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--ref-mode',type=int,default=3);ap.add_argument('--pull',type=int,default=0);ap.add_argument('--batch',type=int,default=0);ap.add_argument('--depth',type=int,default=64);a=ap.parse_args()
 a.work.mkdir(parents=True,exist_ok=False)
 rec={'schema':'opentallas.hbm_iks_timed.v1','source_commit':os.environ.get('PINNED_SOURCE_COMMIT') or subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
 'input_sha256':{s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in SRC+['tools/hbm_svc_iks_binding_bench.py','results/rtl/hbm_index_service_20261008/binding_before_bench.json']},
 'scope':'timed request-level controller; behavioral return SRAM, no physical signoff or performance adoption',
 'controller':f'ot_hdc_v41x_idx_hbm NPC32 REFPB{a.ref_mode} PULL{a.pull} BATCH{a.batch} MEM_MODE1 QD64 TCK1024ps',
 'sector_reservation_depth':a.depth,
 'cases':[],'verdict':'INCOMPLETE'}
 a.out.parent.mkdir(parents=True,exist_ok=True)
 def save():a.out.write_text(json.dumps(rec,indent=2)+'\n')
 save()
 exe=a.work/'obj/Vtb_hbm_svc_iks_binding'
 v=os.environ.get('VERILATOR',str(Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator'))
 rec['simulator']=subprocess.check_output([v,'--version'],text=True).strip()
 with (a.work/'build.log').open('w') as log:
  cp=subprocess.run([v,'--binary','--timing','-Wno-fatal','-Wno-WIDTH','-j','4','-O2','--top-module','tb_hbm_svc_iks_binding',f'-GREF_MODE={a.ref_mode}',f'-GPULL={a.pull}',f'-GBATCH={a.batch}',f'-GKEY_DEPTH={a.depth}','--Mdir',str(a.work/'obj')]+[str(ROOT/s) for s in SRC],stdout=log,stderr=subprocess.STDOUT)
 rec['build_returncode']=cp.returncode;save()
 if cp.returncode:rec['verdict']='BUILD_FAIL';save();return 1
 for phase,delay,mut in [(p,1,0) for p in [0,1300,2700,4100,5500,6900]]+[(4100,23,0),(0,1,1)]:
  logpath=a.work/f'phase{phase}_delay{delay}_mut{mut}.log'
  with logpath.open('w') as log:cp=subprocess.run([str(exe),f'+phase_ns={phase}',f'+credit_delay={delay}',f'+mut={mut}'],stdout=log,stderr=subprocess.STDOUT)
  raw=logpath.read_text();rows=[]
  for m in re.finditer(r'IKS_TIMED rep=(\d+) .*?last_line_ns=([\d.]+) drain_ns=([\d.]+) logical_tbs=([\d.]+)',raw):
   rows.append(dict(rep=int(m[1]),last_line_ns=float(m[2]),drain_ns=float(m[3]),logical_tbs=float(m[4])))
  passed=cp.returncode==0 and 'PASS_HBM_SVC_IKS_TIMED' in raw and len(rows)==2
  # A data-negative must fail at the byte checker, not at elaboration/protocol timeout.
  rejected=cp.returncode!=0 and 'data line=' in raw
  rec['cases'].append(dict(phase_ns=phase,credit_delay=delay,mut=mut,ref_mode=a.ref_mode,pull=a.pull,batch=a.batch,returncode=cp.returncode,raw_log=logpath.name,raw_sha256=hashlib.sha256(logpath.read_bytes()).hexdigest(),rows=rows,diagnostics=re.findall(r'IKS_BINDING .*',raw),gate_passed=rejected if mut else passed));save()
 rec['verdict']='PASS' if all(x['gate_passed'] for x in rec['cases']) else 'FAIL';save();print(rec['verdict'],flush=True)
 return 0 if rec['verdict']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
