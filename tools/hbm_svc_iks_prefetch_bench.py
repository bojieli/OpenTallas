#!/usr/bin/env python3
"""Actual IKS service, timed REFpb controller, exact bytes and final credits.
Run on an admitted remote host, never a shared checkout. Retain all raw logs.
"""
import argparse, hashlib, json, os, re, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SRC=['rtl/hbm_accel/service/ot_hbm_accel_cdc_fifo.sv','rtl/hbm_accel/service/ot_hbm_kport_map.sv',
'physical/hbm_accel_die_views/svc/rtl/ot_hbm_index_lines.sv','physical/hbm_accel_die_views/svc/rtl/ot_hbm_svc_core.sv',
'rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv','physical/hbm_accel_die_views/index/rtl/hfd_idx_lib.sv','rtl/common/ot_secded.sv','rtl/common/ot_secded_cols.svh','rtl/hbm_accel/service/ot_hbm_accel_cdc_fifo_p2.sv','rtl/hbm_accel/service/ot_hbm_index_line_cdc.sv','rtl/hbm_accel/service/ot_hbm_index_prefetch.sv','rtl/test/hbm_accel/tb_hbm_svc_iks_prefetch.sv','rtl/hbm_accel/control/ot_hbm_native_index_control.sv']
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--work',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--ref-mode',type=int,default=3);ap.add_argument('--pull',type=int,default=0);ap.add_argument('--batch',type=int,default=0);ap.add_argument('--depth',type=int,default=64);ap.add_argument('--maxread',type=int,default=15);ap.add_argument('--code-mut',type=int,default=0);ap.add_argument('--portal',type=int,default=0);ap.add_argument('--control',type=int,default=0);ap.add_argument('--early',type=int,default=0);a=ap.parse_args()
 a.work.mkdir(parents=True,exist_ok=False)
 rec={'schema':'opentallas.hbm_iks_prefetch_fifo.v1','source_commit':os.environ.get('PINNED_SOURCE_COMMIT') or subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
 'input_sha256':{s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in SRC+['tools/hbm_svc_iks_prefetch_bench.py','results/rtl/hbm_index_service_20261008/binding_before_bench.json']},
 'scope':'actual1024psHBM service to actual833ps scorer FA6 through protectedfinitecodedCDC and24stationrelays; heldquery sensitivities only, no physical adoption',
 'controller':f'ot_hdc_v41x_idx_hbm NPC32 REFPB{a.ref_mode} PULL{a.pull} BATCH{a.batch} MEM_MODE1 QD64 TCK1024ps BURST1024ps SCORE833ps',
 'query_window_bound':False,'dedicated_portal':a.portal,'actual_dynamic_controller':a.control,'early_next_frame':a.early,'full342_gate_only':True,'query_producer_window_bound':False,'sector_reservation_depth':a.depth,'maximum_inflight_read_requests':a.maxread,
 'cases':[],'verdict':'INCOMPLETE'}
 a.out.parent.mkdir(parents=True,exist_ok=True)
 def save():a.out.write_text(json.dumps(rec,indent=2)+'\n')
 save()
 exe=a.work/'obj/Vtb_hbm_svc_iks_prefetch'
 v=os.environ.get('VERILATOR',str(Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator'))
 rec['simulator']=subprocess.check_output([v,'--version'],text=True).strip()
 with (a.work/'build.log').open('w') as log:
  cp=subprocess.run([v,'--binary','--timing','-Wno-fatal','-Wno-WIDTH','-j','4','-O2','-I'+str(ROOT/'rtl/common'),'--top-module','tb_hbm_svc_iks_prefetch',f'-GREF_MODE={a.ref_mode}',f'-GPULL={a.pull}',f'-GBATCH={a.batch}',f'-GKEY_DEPTH={a.depth}',f'-GMAXREAD={a.maxread}',f'-GCODE_MUT={a.code_mut}',f'-GPORTAL={a.portal}',f'-GCONTROL={a.control}',f'-GEARLY={a.early}','--Mdir',str(a.work/'obj')]+[str(ROOT/s) for s in SRC if not s.endswith('.svh')],stdout=log,stderr=subprocess.STDOUT)
 rec['build_returncode']=cp.returncode;save()
 if cp.returncode:rec['verdict']='BUILD_FAIL';save();return 1
 cases=([(0,300,0,0)] if a.code_mut else [(0,q,0,0) for q in [0,100,300,1000]]+[(4100,300,0,0),(4100,1000,0,0),(6900,300,0,0),(0,300,0,125),(0,300,0,625),(0,300,1,0)])
 if a.portal:cases=[(0,300,0,0),(0,1000,0,0),(4100,300,0,0),(0,300,1,0)]
 if a.early:cases=[(0,300,0,0)]
 for phase,delay,mut,score_phase in cases:
  logpath=a.work/f'phase{phase}_delay{delay}_mut{mut}_scorephase{score_phase}.log'
  with logpath.open('w') as log:cp=subprocess.run([str(exe),f'+phase_ns={phase}',f'+query_ns={delay}',f'+mut={mut}',f'+score_phase_ps={score_phase}'],stdout=log,stderr=subprocess.STDOUT)
  raw=logpath.read_text();rows=[]
  for m in re.finditer(r'IKS_PREFETCH rep=(\d+) .*?max_fifo=(\d+) last_line_ns=([\d.]+) exposed_after_query_ns=([\d.]+)',raw):
   rows.append(dict(rep=int(m[1]),max_fifo=int(m[2]),last_line_ns=float(m[3]),exposed_after_query_ns=float(m[4])))
  passed=cp.returncode==0 and 'PASS_HBM_SVC_IKS_PREFETCH' in raw and len(rows)==2
  # A data-negative must fail at the byte checker, not at elaboration/protocol timeout.
  rejected=cp.returncode!=0 and ('coded crossing poisoned' in raw if a.code_mut==3 else 'data line=' in raw)
  rec['cases'].append(dict(phase_ns=phase,query_hold_ns=delay,mut=mut,code_mut=a.code_mut,score_phase_ps=score_phase,ref_mode=a.ref_mode,pull=a.pull,batch=a.batch,returncode=cp.returncode,raw_log=logpath.name,raw_sha256=hashlib.sha256(logpath.read_bytes()).hexdigest(),rows=rows,diagnostics=re.findall(r'IKS_BINDING .*',raw),gate_passed=rejected if mut or a.code_mut==3 else passed));save()
 rec['verdict']='PASS' if all(x['gate_passed'] for x in rec['cases']) else 'FAIL';save();print(rec['verdict'],flush=True)
 return 0 if rec['verdict']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
