"""Link a read-only observer against immutable completed Verilator model objects.
No HDL, arithmetic, reset equation or event scheduling is changed. A copied
archive has only its original main entrypoint symbol renamed to avoid collision.
"""
from pathlib import Path
import subprocess,hashlib
inc=Path.home()/'.local/opentallas-tools/verilator-5.050/share/verilator/include'
for directory,top,field in [('numeric','tb_qwen_a0_reset_native','errors'),('numeric_r6','tb_qwen_a0_reset_native_r6','idle_payload_differences')]:
 obj=Path(directory)/'obj'; out=Path('intervals')/directory;out.mkdir(parents=True,exist_ok=True)
 prefix='V'+top
 cpp=f'''#include "verilated.h"
#include "{prefix}.h"
#include "{prefix}___024root.h"
#include <cstdio>
int main(int argc,char**argv){{
 const std::unique_ptr<VerilatedContext> c{{new VerilatedContext}};
 c->threads(1);c->commandArgs(argc,argv);
 const std::unique_ptr<{prefix}> t{{new {prefix}{{c.get(),""}}}};
 unsigned last=0;
 while(!c->gotFinish()){{
  t->eval();
  auto*r=t->rootp;
  unsigned now=r->{top}__DOT__{field};
  if(now!=last){{
   unsigned check=r->{top}__DOT__checks;
   unsigned cyc={"(check<=6399?check+100:check-6399+6640)" if directory=='numeric' else "check-1"};
   unsigned ev=r->{top}__DOT__rt_prev[16]&1;
   unsigned av=r->{top}__DOT__ut[16]&1;
   std::printf("A0_INTERVAL cycle%u event%u time%llu expected_valid%u actual_valid%u\\n",cyc,now,(unsigned long long)c->time(),ev,av);std::fflush(stdout);
   last=now;
  }}
  if(!t->eventsPending())break;
  c->time(t->nextTimeSlot());
 }}
 t->final();return 0;
}}
'''
 source=out/'observer.cpp';source.write_text(cpp)
 copied=out/'model_observer.a'
 subprocess.run(['objcopy','--redefine-sym','main=a0_original_main',str(obj/(prefix+'__ALL.a')),str(copied)],check=True)
 cmd=['g++','-std=c++20','-fcoroutines','-O1','-I'+str(obj.resolve()),'-I'+str(inc),'-I'+str(inc/'vltstd'),str(source),str(copied),str(obj/'verilated.o'),str(obj/'verilated_timing.o'),str(obj/'verilated_threads.o'),'-pthread','-latomic','-o',str(out/'observer')]
 subprocess.run(cmd,check=True)
 paths=[source,obj/(prefix+'__ALL.a'),copied,obj/(prefix+'___024root.h'),out/'observer']
 (out/'source.sha256').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+str(p)+'\n' for p in paths))
 with (out/'run.log').open('w') as f:r=subprocess.run([str(out/'observer'),'+MUT=0'],stdout=f,stderr=subprocess.STDOUT)
 assert (r.returncode!=0)==(directory=='numeric'),r.returncode
 lines=[s for s in (out/'run.log').read_text().splitlines() if s.startswith('A0_INTERVAL ')]
 assert len(lines)==(95 if directory=='numeric' else 72),len(lines)
 assert all('expected_valid0 actual_valid0' in s for s in lines)
 print('A0_IDLE_INTERVAL_PASS',directory,len(lines),lines[0],lines[-1])
