#include "verilated.h"
#include "Vtb.h"
#include "Vtb___024root.h"
#include <cstdio>
#include <cstdlib>
int main(int argc,char**argv){
 auto c=std::make_unique<VerilatedContext>();c->threads(1);c->commandArgs(argc,argv);auto t=std::make_unique<Vtb>(c.get(),"");bool ps=0,pq=0;const char* a=c->commandArgsPlusMatch("CONTROL=");int k=(*a?atoi(a+9):0);bool reset_sent=false;uint64_t reset_time=0;
 while(!c->gotFinish()){
 t->eval();auto r=t->rootp;
 if(pq&&!r->tb__DOT__clk){
 if(k==5&&r->tb__DOT__qt==2700){printf("OVERLAP_START qt2700 busy=%u first_request_active\n",r->tb__DOT__rel__DOT__b_s);r->tb__DOT__start=1;}
 if(k==5&&r->tb__DOT__qt==2701)r->tb__DOT__start=0;
 if((r->tb__DOT__qt>=2660&&r->tb__DOT__qt<=2750)||(r->tb__DOT__qt>=2958&&r->tb__DOT__qt<=3050)){
 printf("ADMIT qt=%u st=%u start=%u busy_pin_q=%u valid_mask=%u pc0=%u edge=%u n=%u faults=%u%u%u%u bridge=%u phase=%u\n",r->tb__DOT__qt,r->tb__DOT__st,r->tb__DOT__start,r->tb__DOT__rel__DOT__b_s,r->tb__DOT__dut__DOT__l_valid,r->tb__DOT__dut__DOT__g_c__BRA__0__KET____DOT__u_c__DOT__u_p__DOT__pc,r->tb__DOT__dut__DOT__l_edge__BRA__15__03a0__KET__,r->tb__DOT__n,r->tb__DOT__fault,r->tb__DOT__sfault,r->tb__DOT__tf,r->tb__DOT__cf,r->tb__DOT__brfault,r->tb__DOT__bridge__DOT__phase);fflush(stdout);}}
 if(ps&&!r->tb__DOT__stream){
 if(k==6&&!reset_sent&&r->tb__DOT__st==3830){printf("RESET_NEW_EPOCH stream3830 no_reinstall_negative\n");r->tb__DOT__por_n=0;reset_sent=true;reset_time=c->time();}

 }
 if(k==6&&reset_sent&&c->time()>=reset_time+1668)r->tb__DOT__por_n=1;
 ps=r->tb__DOT__stream;pq=r->tb__DOT__clk;if(!t->eventsPending())break;c->time(t->nextTimeSlot());
 }t->final();return 0;
}
