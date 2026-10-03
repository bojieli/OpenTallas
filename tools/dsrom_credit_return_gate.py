#!/usr/bin/env python3
"""Small actual RTL gates. Never substitutes fixtures for L0/L20 gates."""
import argparse,hashlib,json,os,re,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SOURCES=['rtl/v41rom/ot_v41_ret.sv','rtl/v41rom/ot_v41_ret_credit.sv','rtl/v41die/ot_v41_retn_w17w10.sv','rtl/v41die/ot_v41_retn_credit.sv','rtl/proto/ot_fp32_add_rne_pipe.sv','rtl/hdc/ot_hdc_delay.sv']
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 paths=SOURCES+['rtl/test/tb_dsrom_credit_return.sv','rtl/test/tb_dsrom_credit_root.sv','tools/gen_dsrom_credit_return.py','tools/dsrom_credit_return_gate.py']
 pins={x:hashlib.sha256((ROOT/x).read_bytes()).hexdigest() for x in paths}
 results={};start=time.monotonic()
 for name,top in [('nodes','tb_dsrom_credit_return'),('root','tb_dsrom_credit_root')]:
  exe=a.out/name;bench=f'rtl/test/{top}.sv';cmd=['iverilog','-g2012','-s',top,'-o',str(exe),*[str(ROOT/x) for x in SOURCES],str(ROOT/bench)]
  build=subprocess.run(cmd,capture_output=True,text=True);(a.out/(name+'.compile.log')).write_text(build.stdout+build.stderr)
  if build.returncode:results[name]=dict(compile_exit=build.returncode,status='FAIL_COMPILE');continue
  run=subprocess.run(['/usr/bin/time','-v','vvp',str(exe)],capture_output=True,text=True)
  (a.out/(name+'.run.log')).write_text(run.stdout);(a.out/(name+'.resources.log')).write_text(run.stderr)
  summary=[x for x in run.stdout.splitlines() if x.startswith('RESULT')]
  results[name]=dict(compile_exit=0,run_exit=run.returncode,status='PASS_DIRECTED_RTL' if run.returncode==0 else 'FAIL_RTL',summary=summary)
  if name=='nodes' and run.returncode==0:
   fields={k:int(v) for k,v in re.findall(r'(\w+)=(\d+)',summary[-1])};results[name]['measured']=fields
   results[name]['fixture_latency_increase_fraction']=fields['credit_last']/fields['reference_last']-1
   results[name]['fixture_rate_loss']=1-fields['reference_last']/fields['credit_last']
   launches=[tuple(map(int,x.split()[1:])) for x in run.stdout.splitlines() if x.startswith('LAUNCH')]
   pops=[tuple(map(int,x.split()[1:])) for x in run.stdout.splitlines() if x.startswith('PARENT_POP')]
   lm={row:t for t,row in launches};d=[t-lm[row] for t,row in pops]
   results[name]['measured_launch_to_downstream_pop_cycles']=dict(min=min(d),max=max(d))
   # At saturation all four initial downstream slots are reserved. The first
   # freed slot funds the fifth result, which is accepted/pop'ed later.
   results[name]['measured_saturated_slot_reuse_cycles']=pops[4][0]-pops[0][0]
 # Ragged generated full-target topology metadata and small actual elaboration.
 from gen_dsrom_credit_return import topology,rtl
 for np,r in [(5,2),(2682,128),(4096,128)]:
  t=topology(np,r);results[f'topology_{np}']=dict(nodes=len(t['nodes']),roots=len(t['roots']),padding_pairs=0)
 gen=a.out/'ragged5.sv';gen.write_text(rtl(topology(5,2)))
 comp=subprocess.run(['iverilog','-g2012','-s','ot_v41_return_credit_generated','-o',str(a.out/'ragged5'),*[str(ROOT/x) for x in SOURCES],str(gen)],capture_output=True,text=True)
 (a.out/'ragged5.compile.log').write_text(comp.stdout+comp.stderr)
 results['ragged_elaboration']=dict(compile_exit=comp.returncode,NP=5,R=2,scope='actual RTL compile only; full2682 HDL not built')
 stable=all(hashlib.sha256((ROOT/x).read_bytes()).hexdigest()==v for x,v in pins.items())
 record=dict(label='MEASURED_DIRECTED_RTL_NOT_PROGRAM_GATE',source_sha256=pins,source_stable=stable,results=results,wall_s=time.monotonic()-start,
  L0_exact=None,L20_exact=None,L0_L20_occupancy=None,busiest_stage_rate_loss=None,ASAP7_SS_area_mm2=None,route=None,SS_setup=None,FF_hold=None,adopted=False)
 (a.out/'result.json').write_text(json.dumps(record,indent=2,sort_keys=True)+'\n');print(json.dumps(record,indent=2))
 return 0 if stable and all(results[x]['status']=='PASS_DIRECTED_RTL' for x in ('nodes','root')) and comp.returncode==0 else 1
if __name__=='__main__':raise SystemExit(main())
