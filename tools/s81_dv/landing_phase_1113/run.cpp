#include "Vtb_landing_phase.h"
#include "verilated.h"
#include <algorithm>
#include <array>
#include <cstdio>
#include <cstdlib>
#include <vector>
static constexpr long T=833000;
static std::array<unsigned,6> word(unsigned n){
 return {n,n^0xabcdef01U,n*37U,n^0x87654321U,n*93U,((n*13U)&0xffffU)|(((n/37)&1U)<<16)};
}
int main(int argc,char**argv){
 Verilated::commandArgs(argc,argv);long phase=argc>1?atol(argv[1]):83000;
 if(phase<0||phase>=T)return 2;
 Vtb_landing_phase m;m.fclk=0;m.clk=0;m.rst_n=0;for(int i=0;i<6;i++)m.d[i]=0;m.eval();
 std::vector<long>times;
 for(long n=0;n<1200;n++)for(long t:{n*T,n*T+T/2,n*T+phase,n*T+phase+T/2})times.push_back(t);
 std::sort(times.begin(),times.end());times.erase(std::unique(times.begin(),times.end()),times.end());
 unsigned errors=0,checks=0,wrongedge=0,wrongphase=0;long minage=10000000000L,maxage=0;
 for(long t:times){
  bool fr=t%T==0,ff=t%T==T/2,rr=t>=phase&&(t-phase)%T==0,rf=t>=phase&&(t-phase)%T==T/2;
  if(ff)m.fclk=0;if(rf)m.clk=0;
  if(fr){auto w=word(t/T+1);for(int i=0;i<6;i++)m.d[i]=w[i];m.fclk=1;}
  if(rr){long edge=(t-phase)/T;m.rst_n=(edge>=47&&!(edge>=600&&edge<608));m.clk=1;}
  m.eval();
  if(rr&&m.ready){
   unsigned id=m.q[0];long age=t-(long(id)-1)*T;auto want=word(id);
   bool good=id>0;for(int i=0;i<6;i++)good&=m.q[i]==want[i];
   good&=age==3*T+phase||(phase==0&&age==4*T);good&=!m.fault;
   if(!good&&errors++<4)printf("BAD phase=%ld t=%ld id=%u age=%ld fault=%u\n",phase,t,id,age,(unsigned)m.fault);
   checks++;minage=std::min(minage,age);maxage=std::max(maxage,age);
   if(m.bad_q[0]!=id)wrongedge++;
   if(age!=3*T+phase+1)wrongphase++;
  }
 }
 printf("LANDING_PHASE phase_fs=%ld checks=%u errors=%u age_min_fs=%ld age_max_fs=%ld wrongedge_mismatches=%u wrongphase_mismatches=%u\n",phase,checks,errors,minage,maxage,wrongedge,wrongphase);
 return errors||checks<500?1:0;
}
