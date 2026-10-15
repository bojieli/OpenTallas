#!/usr/bin/env python3
"""Actual original issue_pq lockstep for offline fixed IL-phase pauses."""
import argparse,json,subprocess
from pathlib import Path
import compile_hbm_smh_issue_static as C
import hbm_smh_issue_static_gate as G
def run(out):
 out.mkdir(parents=True,exist_ok=True)
 tb=G.TB.replace('reg [26:0] got;','reg [26:0] got;reg paused[0:200000];')
 tb=tb.replace('.w_valid(1\'b1)',".w_valid(!paused[cy])")
 tb=tb.replace('$readmemh(file,expected,0,n-1);','$readmemh(file,expected,0,n-1); $readmemh("pause.hex",paused,0,n-1);')
 (out/'tb.sv').write_text(tb)
 original=(C.ROOT/C.PINNED[0]).read_text();needle='assign xa = gs_q ? gs_xb + ti[XW-1:0] : xa_r;'
 assert original.count(needle)==1
 (out/'mutant.sv').write_text(original.replace(needle,'assign xa = (gs_q ? gs_xb + ti[XW-1:0] : xa_r) ^ 1;'))
 for mutant,source in [(False,C.ROOT/C.PINNED[0]),(True,out/'mutant.sv')]:
  subprocess.run(['iverilog','-g2012','-s','tb','-o',str(out/('mut' if mutant else 'sim')),str(out/'tb.sv'),str(source)],check=True,capture_output=True)
 cases=[]
 for rows,groups in [(9,6),(8,6),(17,3),(1,16)]:
  for gap in [8,16,24,32]:
   o=dict(rows=rows,groups=groups,fmt=1,gs=True,c=8,launch_cycle=1)
   total=len(list(C.issue_slots(o)))
   o['issue_pauses']=[dict(before_advance=i,cycles=gap) for i in range(64,total,64)]
   ss=list(C.issue_slots(o));n=ss[-1]['cycle']+4;exp=[0]*n;paused=[0]*n
   for s in ss:exp[s['cycle']]=(1<<26)|C.control(s)
   accumulated=0
   for pause in o['issue_pauses']:
    at=8+pause['before_advance']+accumulated
    paused[at:at+gap]=[1]*gap;accumulated+=gap
   (out/'case.hex').write_text(''.join(f'{x:07x}\n' for x in exp));(out/'pause.hex').write_text(''.join(f'{x:x}\n' for x in paused))
   args=[f'+FILE={out}/case.hex',f'+R={rows}',f'+G={groups}','+GS=1','+F=1','+L=1',f'+N={n}']
   result=subprocess.run(['vvp',str(out/'sim'),*args],cwd=out,capture_output=True,text=True)
   if result.returncode:raise RuntimeError(str(o)+result.stdout+result.stderr)
   if rows==9 and groups==6 and gap==24:
    bad=subprocess.run(['vvp',str(out/'mut'),*args],cwd=out,capture_output=True,text=True)
    (out/'mutant.log').write_text(bad.stdout+bad.stderr);assert bad.returncode!=0 and 'control cy' in bad.stdout
    commands=C.compile_manifest({'ops':[o]})['commands'];assert len(commands)==600
    (out/'wkv600.programme83.hex').write_text(''.join(f'{w:021x}\n' for w in commands))
   cases.append(dict(rows=rows,groups=groups,gap=gap,advances=total,cycles=n-4))
 (out/'verdict.json').write_text(json.dumps({'status':'PASS','cases':cases,'actual_RTL_address_mutant_rejected':True,'scope':'original issue_pq control only, no cache/refill/controller/arith throughput qualification'},indent=2)+'\n')
 print('STATIC_PAUSE PASS cases16 WKV600commands actualRTLaddressmutantFAIL')
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--out',required=True);run(Path(a.parse_args().out).resolve())
