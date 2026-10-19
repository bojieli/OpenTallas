#include "verilated.h"
#include "Vtb_qwen_a0_reset_native.h"
#include "Vtb_qwen_a0_reset_native___024root.h"
#include <cstdio>
int main(int argc,char**argv){
 const std::unique_ptr<VerilatedContext> c{new VerilatedContext};
 c->threads(1);c->commandArgs(argc,argv);
 const std::unique_ptr<Vtb_qwen_a0_reset_native> t{new Vtb_qwen_a0_reset_native{c.get(),""}};
 unsigned last=0;
 while(!c->gotFinish()){
  t->eval();
  auto*r=t->rootp;
  unsigned now=r->tb_qwen_a0_reset_native__DOT__errors;
  if(now!=last){
   unsigned check=r->tb_qwen_a0_reset_native__DOT__checks;
   unsigned cyc=(check<=6399?check+100:check-6399+6640);
   unsigned ev=r->tb_qwen_a0_reset_native__DOT__rt_prev[16]&1;
   unsigned av=r->tb_qwen_a0_reset_native__DOT__ut[16]&1;
   std::printf("A0_INTERVAL cycle%u event%u time%llu expected_valid%u actual_valid%u\n",cyc,now,(unsigned long long)c->time(),ev,av);std::fflush(stdout);
   last=now;
  }
  if(!t->eventsPending())break;
  c->time(t->nextTimeSlot());
 }
 t->final();return 0;
}
