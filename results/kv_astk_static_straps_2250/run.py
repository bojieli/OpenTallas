from pathlib import Path
import subprocess,concurrent.futures,os,json
d=Path(__file__).resolve().parent
env=dict(os.environ,PATH='/home/ubuntu/.local/opentallas-tools/bin:'+os.environ['PATH'])
def run(i):
 p=d/f'case{i}'
 subprocess.run(['python3',str(d/'head_master_miter.py'),str(d/'old'),str(d/'new'),str(p),'--force-input',f"strap_corner=2'd{i}"],check=True,stdout=(d/f'case{i}.gen.log').open('w'),stderr=subprocess.STDOUT,env=env)
 tb=p/'tb.sv';s=tb.read_text()
 # Keep the released-reset miter intact; count raw reset/startup differences separately.
 s=s.replace('integer n, mis = 0,','integer raw_reset_mis=0; integer n, mis = 0,')
 anchor='  initial begin'
 s=s.replace(anchor,'  always @(negedge ck) if(!rn && vo !== vn) raw_reset_mis=raw_reset_mis+1;\n'+anchor)
 s=s.replace('    $finish;',f'    $display("STATIC_STRAP id={i} RAW_RESET_DIFF=%0d",raw_reset_mis);\n    $finish;')
 tb.write_text(s)
 cmd=['verilator','--binary','--timing','-j','8','-MAKEFLAGS','OBJCACHE=','-Wno-fatal','-Wno-lint','-Wno-style','-Wno-MULTIDRIVEN','-DSYNTHESIS','-Io','-In','--top-module','tb','--Mdir','obj','-f','files.f']
 subprocess.run(cmd,cwd=p,env=env,check=True,stdout=(p/'build.log').open('w'),stderr=subprocess.STDOUT)
 subprocess.run([str(p/'obj/Vtb')],cwd=p,env=env,check=True,stdout=(p/'sim.log').open('w'),stderr=subprocess.STDOUT)
 text=(p/'sim.log').read_text()
 assert ' PASS ' in text,text
 print(i,text,flush=True)
 return text
with concurrent.futures.ThreadPoolExecutor(max_workers=4)as ex:res=list(ex.map(run,range(4)))
(d/'result.json').write_text(json.dumps(dict(verdict='PASS',cases=res,contract='IDs static before reset; raw-reset differences reported separately'),indent=1)+'\n')
