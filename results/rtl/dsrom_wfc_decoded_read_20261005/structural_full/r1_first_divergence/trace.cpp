#include <cstdio>
#include <memory>
#include "verilated.h"
#include "Vtb_wfc_structural_full.h"
#include "Vtb_wfc_structural_full___024root.h"
int main(int argc,char**argv){
 auto c=std::make_unique<VerilatedContext>();c->commandArgs(argc,argv);
 auto t=std::make_unique<Vtb_wfc_structural_full>(c.get(),"");
 while(!c->gotFinish()){
  t->eval(); auto*r=t->rootp;
  if(r->tb_wfc_structural_full__DOT__cyc>=5770){
   printf("OFFER time=%llu clk=%u cyc=%u mism=%u",(unsigned long long)c->time(),r->tb_wfc_structural_full__DOT__clk,r->tb_wfc_structural_full__DOT__cyc,r->tb_wfc_structural_full__DOT__mism);
printf(" lane0:valid=%u ready=%u last=%u sent=%u left=%u data0=%08x data1=%08x data2=%08x",r->tb_wfc_structural_full__DOT__g__BRA__0__KET____DOT__in_valid,r->tb_wfc_structural_full__DOT__g__BRA__0__KET____DOT__in_ready,r->tb_wfc_structural_full__DOT__g__BRA__0__KET____DOT__in_last,r->tb_wfc_structural_full__DOT__g__BRA__0__KET____DOT__stg__DOT__sent,r->tb_wfc_structural_full__DOT__g__BRA__0__KET____DOT__stg__DOT__left,r->tb_wfc_structural_full__DOT__g__BRA__0__KET____DOT__in_data[0],r->tb_wfc_structural_full__DOT__g__BRA__0__KET____DOT__in_data[1],r->tb_wfc_structural_full__DOT__g__BRA__0__KET____DOT__in_data[2]);
printf(" lane1:valid=%u ready=%u last=%u sent=%u left=%u data0=%08x data1=%08x data2=%08x",r->tb_wfc_structural_full__DOT__g__BRA__1__KET____DOT__in_valid,r->tb_wfc_structural_full__DOT__g__BRA__1__KET____DOT__in_ready,r->tb_wfc_structural_full__DOT__g__BRA__1__KET____DOT__in_last,r->tb_wfc_structural_full__DOT__g__BRA__1__KET____DOT__stg__DOT__sent,r->tb_wfc_structural_full__DOT__g__BRA__1__KET____DOT__stg__DOT__left,r->tb_wfc_structural_full__DOT__g__BRA__1__KET____DOT__in_data[0],r->tb_wfc_structural_full__DOT__g__BRA__1__KET____DOT__in_data[1],r->tb_wfc_structural_full__DOT__g__BRA__1__KET____DOT__in_data[2]);
printf(" lane2:valid=%u ready=%u last=%u sent=%u left=%u data0=%08x data1=%08x data2=%08x",r->tb_wfc_structural_full__DOT__g__BRA__2__KET____DOT__in_valid,r->tb_wfc_structural_full__DOT__g__BRA__2__KET____DOT__in_ready,r->tb_wfc_structural_full__DOT__g__BRA__2__KET____DOT__in_last,r->tb_wfc_structural_full__DOT__g__BRA__2__KET____DOT__stg__DOT__sent,r->tb_wfc_structural_full__DOT__g__BRA__2__KET____DOT__stg__DOT__left,r->tb_wfc_structural_full__DOT__g__BRA__2__KET____DOT__in_data[0],r->tb_wfc_structural_full__DOT__g__BRA__2__KET____DOT__in_data[1],r->tb_wfc_structural_full__DOT__g__BRA__2__KET____DOT__in_data[2]);
   puts("");
  }
  if(r->tb_wfc_structural_full__DOT__mism){puts("FIRST_DIVERGENCE_STOP: original full-shape objects, no model/front-end rebuild");break;}
  if(!t->eventsPending())return 2;
  c->time(t->nextTimeSlot());
 }
 return 0;
}
