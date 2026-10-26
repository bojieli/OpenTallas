from pathlib import Path
import subprocess,re,os
w=Path(__file__).resolve().parent
v=str(Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator')
for mode,flag in [('pass',[]),('mut',['-DOT_S81HD_FADD_ZERO_MUT'])]:
 with (w/('build_'+mode+'.log')).open('w')as f:subprocess.run([v,'--binary','--timing','-Wno-fatal','-j','8','--Mdir','obj_'+mode,'--top-module','tb','-DOT_S81HD_FADD_ZERO_ARITH']+flag+['ref.sv','new.sv','prefix.sv','tb.sv'],cwd=w,stdout=f,stderr=subprocess.STDOUT,check=True)
 for seed in [1,2,3]:
  q=subprocess.run([str(w/('obj_'+mode)/'Vtb'),'+seed='+str(seed)],cwd=w,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);(w/(mode+'_'+str(seed)+'.log')).write_text(q.stdout);line=next(x for x in q.stdout.splitlines()if x.startswith('ZERO_ARITH'));print(line,flush=True)
  if mode=='pass' and ' PASS 'not in line:raise SystemExit(1)
  if mode=='mut' and ' FAIL 'not in line:raise SystemExit(2)
print('QUALIFIED specials1024 + mixedzero/subnormal/nonfinite random3seeds; zero bypass mutant CAUGHT all3',flush=True)
