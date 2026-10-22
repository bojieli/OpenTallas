#include "verilated.h"
#include "Vtb.h"
#include "Vtb___024root.h"
#include <cstdio>
int main(int argc,char**argv){
 auto c=std::make_unique<VerilatedContext>();c->threads(1);c->commandArgs(argc,argv);auto t=std::make_unique<Vtb>(c.get(),"");bool ps=0,pq=0;
 while(!c->gotFinish()){
 t->eval();auto r=t->rootp;
 if(ps&&!r->tb__DOT__stream&&((r->tb__DOT__st>=95&&r->tb__DOT__st<=140)||(r->tb__DOT__st>=3800&&r->tb__DOT__st<=3845)||(r->tb__DOT__st>=3960&&r->tb__DOT__st<=4080))){
 printf("VMOBS st=%u hostw=",r->tb__DOT__st);for(int i=8;i>=0;i--)printf("%08x",r->tb__DOT__B__BRA__0__KET____DOT__hostw[i]);
 printf(" wp=%u%u%u wa=%u ra=%u wd=",r->tb__DOT__B__BRA__0__KET____DOT__vm__DOT__u_ot_pr_core__DOT__bank__DOT__m_wA,r->tb__DOT__B__BRA__0__KET____DOT__vm__DOT__u_ot_pr_core__DOT__bank__DOT__m_wB,r->tb__DOT__B__BRA__0__KET____DOT__vm__DOT__u_ot_pr_core__DOT__bank__DOT__m_wC,r->tb__DOT__B__BRA__0__KET____DOT__vm__DOT__u_ot_pr_core__DOT__bank__DOT__m_wa,r->tb__DOT__B__BRA__0__KET____DOT__vm__DOT__u_ot_pr_core__DOT__bank__DOT__m_ra);
 for(int i=9;i>=0;i--)printf("%08x",r->tb__DOT__B__BRA__0__KET____DOT__vm__DOT__u_ot_pr_core__DOT__bank__DOT__m_wd[i]);printf("\n");fflush(stdout);
 }
 if(pq&&!r->tb__DOT__clk&&((r->tb__DOT__qt>=2690&&r->tb__DOT__qt<=2748)||(r->tb__DOT__qt>=2990&&r->tb__DOT__qt<=3048))){
 printf("LANEOBS qt=%u frv=%u frow=%u dat=",r->tb__DOT__qt,r->tb__DOT__slice__DOT__u_slice__DOT__fr_v,r->tb__DOT__slice__DOT__u_slice__DOT__fr_row[0]);for(int i=7;i>=0;i--)printf("%08x",r->tb__DOT__slice__DOT__u_slice__DOT__fr_dat[0][i]);
 printf(" live=%u f_v=%u f_d1=%x wpin=%u wa=%u wd=%x raw=",r->tb__DOT__slice__DOT__u_slice__DOT__g_lane__BRA__0__KET____DOT__g_plain__DOT__u_lane__DOT__live0,r->tb__DOT__slice__DOT__u_slice__DOT__g_lane__BRA__0__KET____DOT__g_plain__DOT__u_lane__DOT__f_v,r->tb__DOT__slice__DOT__u_slice__DOT__g_lane__BRA__0__KET____DOT__g_plain__DOT__u_lane__DOT__f_d1,r->tb__DOT__slice__DOT__u_slice__DOT__g_bank__BRA__0__KET____DOT__u_bank__DOT__w_pin,r->tb__DOT__slice__DOT__u_slice__DOT__g_bank__BRA__0__KET____DOT__u_bank__DOT__wa_pin,r->tb__DOT__slice__DOT__u_slice__DOT__g_bank__BRA__0__KET____DOT__u_bank__DOT__wd_pin);
 for(int i=7;i>=0;i--)printf("%08x",r->tb__DOT__slice__DOT__u_slice__DOT__g_bank__BRA__0__KET____DOT__u_bank__DOT__u_data__DOT__g_read__BRA__0__KET____DOT__raw[i]);printf("\n");fflush(stdout);
 }
 ps=r->tb__DOT__stream;pq=r->tb__DOT__clk;if(!t->eventsPending())break;c->time(t->nextTimeSlot());
 }t->final();return 0;
}
