from pathlib import Path
import subprocess,json,re
O=Path.cwd();A=Path('/srv/opentallas-scratch/claude/hbm-native-record23-clock-1019/obj_arithmetic_clock');R=Path('/srv/opentallas-scratch/claude/hbm-record23-repair-1019');V=Path('/home/ubuntu/.local/opentallas-tools/verilator-5.050/share/verilator/include')
subprocess.run(['objcopy','--redefine-sym','main=baseline_main',str(O/'Vtb__ALL.a'),str(O/'controls.a')],check=True)
subprocess.run(['g++','-std=c++20','-O0','-DVL_TIME_CONTEXT','-I'+str(A),'-I'+str(V),'-I'+str(V/'vltstd'),'-pthread',str(O/'event_controls.cpp'),str(O/'controls.a'),str(A/'verilated.o'),str(A/'verilated_threads.o'),str(A/'verilated_timing.o'),'-latomic','-o',str(O/'event_controls')],check=True)
args=[f'+CFG={R}/production/cols/config.mem',f'+GOLD={R}/production/quarter.mem','+N=73','+W=70']
summary=[]
for k,name in [(0,'positive_admission'),(1,'stale_input'),(2,'missing_descriptor'),(3,'host_identity_swap'),(4,'restart_phase'),(5,'overlap'),(6,'reset_without_reinstall')]:
 p=O/(name+'.log')
 with p.open('w')as f:r=subprocess.run([str(O/'event_controls'),*args,f'+REQMUT={k}',f'+CONTROL={k}'],stdout=f,stderr=subprocess.STDOUT)
 s=p.read_text();ok=(r.returncode==0 and 'SERIAL_REQUESTS2 PASS' in s)if k==0 else(r.returncode!=0 and ('ARITHMETIC FAIL' in s or 'PRODUCER FAIL' in s or 'FIXED_EVENT_HORIZON' in s))
 summary.append(dict(case=name,returncode=r.returncode,expected_fail=k!=0,matched=ok,first_fatal=next((x for x in s.splitlines()if '%Fatal' in x),None)))
 print('CAUSAL',name,r.returncode,ok,flush=True)
 (O/'causal_summary.json').write_text(json.dumps(summary,indent=2))
 assert ok,summary[-1]
