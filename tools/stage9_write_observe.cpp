// Observe the retained failed model without changing any input or model source.
#include "Vtb_dsrom_wavefront_array.h"
#include "Vtb_dsrom_wavefront_array___024root.h"
#include "verilated.h"
#include <cstdio>
static vluint64_t sim_time=0;
double sc_time_stamp(){return static_cast<double>(sim_time);}
#define K(x) root->tb_dsrom_wavefront_array__DOT__g_node__BRA__0__KET____DOT__g_pooled_idx__DOT__g_kv_hbm__DOT__u_kv__DOT__##x
#define N(x) root->tb_dsrom_wavefront_array__DOT__g_node__BRA__0__KET____DOT__##x
int main(int argc,char**argv){
 Verilated::commandArgs(argc,argv);
 auto* top=new Vtb_dsrom_wavefront_array;
 auto* root=top->rootp;
 top->clk=0;
 while(!Verilated::gotFinish()){
  if(!top->clk && sim_time){
   if(N(core__DOT__g_su_x__DOT__u_su__DOT__u_vec__DOT__b_dst)>=2)
    std::printf("KV_VECTOR time=%llu pc=%u pos=%u corebase=%u corerow=%u base=%u row=%u inner=%u dst=%u\n", (unsigned long long)sim_time,N(core__DOT__pc),N(core__DOT__pos_r),N(core__DOT__o_base),N(core__DOT__o_row),N(core__DOT__g_su_x__DOT__u_su__DOT__u_vec__DOT__b_obase),N(core__DOT__g_su_x__DOT__u_su__DOT__u_vec__DOT__b_krow),N(core__DOT__g_su_x__DOT__u_su__DOT__u_vec__DOT__b_iv),N(core__DOT__g_su_x__DOT__u_su__DOT__u_vec__DOT__b_dst));
   for(unsigned i=0;i<24;++i)if(K(l_v)[i]&&K(l_word)[i]>=32768)
    std::printf("BAD_PRODUCER time=%llu lane=%u kind=%s base=%u word=%u scalar=%u data=%08x\n",
      (unsigned long long)sim_time,i,i<8?"stream":"SU",N(kv_base),K(l_word)[i],
      ((K(l_word)[i]-N(kv_base))<<4)|K(l_lane)[i],K(l_data)[i]);
   for(unsigned s=0;s<4;++s)if((K(wq_pop)&(1u<<s))&&
      (K(wq_haddr)[s]<262144||K(wq_haddr)[s]>=278528)){
     auto rp=K(wq_rp)[s];auto hs=K(wq_sec)[s*128+rp];
     std::printf("BAD_QUEUE time=%llu base=%u stack=%u pop=%u n=%u rp=%u hs=%u word=%u half=%u haddr=%u strobes=%08x\n",
       (unsigned long long)sim_time,N(kv_base),s,K(wq_pop),K(wq_n)[s],rp,hs,hs>>1,hs&1,
       K(wq_haddr)[s],K(wq_s)[s*128+rp]);
     std::fflush(stdout);return 78;
   }
  }
  top->clk=!top->clk;top->eval();++sim_time;
 }
 top->final();delete top;return 0;
}
