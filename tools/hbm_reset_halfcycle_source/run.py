import subprocess,json,hashlib,time,resource
from pathlib import Path
p=Path('.')
def run(name,define='',adapter=None):
 d=p/name;d.mkdir(exist_ok=True)
 a=adapter or Path('native_equation_adapter.v').read_text();(d/'adapter.v').write_text(a)
 cmd=['iverilog','-g2012','-s','bench','-o',str(d/'sim')]
 if define:cmd+=['-D'+define]
 b=subprocess.run(cmd+['pair.v',str(d/'adapter.v'),'bench.v'],capture_output=True,text=True)
 assert b.returncode==0,b.stderr
 q=subprocess.run(['vvp',str(d/'sim')],capture_output=True,text=True)
 log=b.stdout+b.stderr+q.stdout+q.stderr;(d/'witness.log').write_text(log)
 good=name=='baseline'
 assert (q.returncode==0)==good,(name,q.returncode,log)
 assert ('FUNCTIONAL_PASS' if good else 'FUNCTIONAL_FAIL') in log
 return dict(name=name,returncode=q.returncode,witness_sha256=hashlib.sha256(log.encode()).hexdigest())
t=time.time();a=Path('native_equation_adapter.v').read_text()
r=[run('baseline')]
for name,d in [('mut_missing_clock_inv','MUT_NO_CLOCK_INV'),('mut_raw_ff2_reset','MUT_RAW_FF2_RESET'),('mut_ownership','MUT_OWNERSHIP')]:r.append(run(name,d))
r.append(run('mut_wrong_output_polarity',adapter=a.replace('module INVx6_ASAP7_75t_R(input A,output Y); assign Y=~A;', 'module INVx6_ASAP7_75t_R(input A,output Y); assign Y=A;')))
Path('simulation_receipt.json').write_text(json.dumps(dict(status='FUNCTIONAL_ONLY_PHYSICAL_HOLD',runs=r,wall_s=time.time()-t,maxrss_kb=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,tool=subprocess.run(['iverilog','-V'],capture_output=True,text=True).stdout.splitlines()[0]),indent=2)+'\n')
print(json.dumps(r))
