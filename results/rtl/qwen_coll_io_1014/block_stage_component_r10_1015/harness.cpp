#include "Vtb_qfd_ucie_six_five.h"
#include "verilated.h"
#include <cstdint>
#include <cstdio>
#include <cstdlib>
// tick = 5 ns / 30: core every 5 ticks, FDI every 6 (+FPHI), block every 30.
// rst_n releases at tick REL (between edges); words are offered from core
// edge N0 after release; output must equal input 19 core edges later.
uint32_t word(int c,int j){return uint32_t(c*0x9e3779b9u)^uint32_t(j*0x85ebca6bu)^0xdeadbeefu;}
int main(int argc,char**argv){Verilated::commandArgs(argc,argv);int bad=0,checks=0,faults=0,cases=0;
 int fphi=0;const char*e=getenv("FPHI");if(e)fphi=atoi(e);const int N0=24,LAT=19;
 for(int rel=0;rel<30;rel++){auto*t=new Vtb_qfd_ucie_six_five;t->rst_n=0;t->core_ck=0;t->fdi_ck=0;t->blk_ck=0;t->tx_valid=0;t->eval();
 int c=-1,local=0,validseen=0;
 for(int tick=0;tick<30*1200;tick++){
  if(tick==60+rel){t->rst_n=1;t->eval();c=0;}
  bool ce=tick%5==0,fe=(tick+30-fphi)%6==0,be=tick%30==0;
  if(ce&&c>=0){t->tx_valid=(c>=N0)&&(c%11<8);for(int j=0;j<19;j++)t->tx_frame[j]=word(c,j);t->tx_frame[18]&=0x1fffff;}
  t->core_ck=ce;t->fdi_ck=fe;t->blk_ck=be;t->eval();
  if(ce&&c>=0){int x=c-LAT;bool ev=(x>=N0)&&(x%11<8);checks++;
   if(t->rx_valid!=ev)local++;
   if(ev){validseen++;for(int j=0;j<19;j++){uint32_t w=word(x,j);if(j==18)w&=0x1fffff;if(t->rx_frame[j]!=w)local++;}}
   c++;}
  t->core_ck=0;t->fdi_ck=0;t->blk_ck=0;t->eval();}
 int fault=t->core_fault||t->fdi_fault;faults+=fault;bad+=local;cases++;
 printf("release_tick=%d corecycles=%d validwords=%d mismatches=%d corefault=%d fdifault=%d\n",rel,c,validseen,local,int(t->core_fault),int(t->fdi_fault));delete t;}
 printf("cases=%d checks=%d mismatches=%d faults=%d\n",cases,checks,bad,faults);return (bad||faults)?1:0;}
