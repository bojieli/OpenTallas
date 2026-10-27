#include <memory>
#include <cstdio>
#include "verilated.h"
#include "Vtb_native_boot.h"
#include "Vtb_native_boot___024root.h"
int main(int argc,char**argv){
 auto c=std::make_unique<VerilatedContext>();c->threads(1);c->commandArgs(argc,argv);
 auto t=std::make_unique<Vtb_native_boot>(c.get(),"");
 bool last[5]={};unsigned start=0;
 const char* names[]={"host_ingress_launch","provider_start_pin","job217_pin","native_root_done","programme_done"};
 while(!c->gotFinish()){
  t->eval();auto*r=t->rootp;
  bool v[]={bool(r->tb_native_boot__DOT__lv),bool(r->tb_native_boot__DOT__programme__DOT__start),bool(r->tb_native_boot__DOT__jv),bool(r->tb_native_boot__DOT__rdone),bool(r->tb_native_boot__DOT__done)};
  for(int i=0;i<5;i++){if(v[i]&&!last[i])std::printf("NATIVE_BOOT_DATE event=%s edge=%u\n",names[i],r->tb_native_boot__DOT__cc-1);last[i]=v[i];}
  if(r->tb_native_boot__DOT__start_edge!=start){start=r->tb_native_boot__DOT__start_edge;std::printf("NATIVE_BOOT_DATE event=provider_START_capture edge=%u\n",start);}
  if(!t->eventsPending())break;c->time(t->nextTimeSlot());
 }
 t->final();return 0;
}
