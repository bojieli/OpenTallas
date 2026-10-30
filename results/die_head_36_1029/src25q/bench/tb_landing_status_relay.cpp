#include "Vtb_landing_status_relay.h"
#include "verilated.h"
#include <cstdio>
// out(t) must equal ref(t-3) once the pipeline is out of reset (reset clears every stage: ready 0, fault 0);
// a sticky source fault is held at the pin; ready reaches the pin exactly 3 cycles after the depth-1 form.
int main(int argc,char**argv){Verilated::commandArgs(argc,argv);Vtb_landing_status_relay m;
  unsigned errors=0,checks=0;int hr[4096],hf[4096],orr[4096],of[4096];
  for(int k=0;k<4096;k++){bool rst=k>=4&&!(k>=2000&&k<2006);unsigned r=(k*7+k/13)&3,f=((k%97)==50)?1:0;
    if(k>3000)f=(k>3500)?2:0;   // sticky-source phase: fault held high from 3501
    m.clk=0;m.rst_n=rst;m.ready_i=r;m.fault_i=f;m.eval();m.clk=1;m.eval();
    hr[k]=m.ready_ref;hf[k]=m.fault_ref;orr[k]=m.ready_o;of[k]=m.fault_o;
    bool settled=(k>=10)&&!(k>=2000&&k<2012);
    if(settled){checks++;if(orr[k]!=hr[k-3]||of[k]!=hf[k-3]){if(errors++<4)printf("DIFF k=%d out=%d/%d ref(k-3)=%d/%d\n",k,orr[k],of[k],hr[k-3],hf[k-3]);}}
    if(!rst&&(m.ready_o||m.fault_o)&&k>=6)errors++; }
  int rf=-1,ro=-1;for(int k=3501;k<4096;k++){if(rf<0&&hf[k])rf=k;if(ro<0&&of[k])ro=k;}
  bool held=true;for(int k=ro;k<4096;k++)held&=of[k]==1;
  printf("fault at ref pin k=%d, at relayed pin k=%d (+%d, expect +3), held=%d\n",rf,ro,ro-rf,held);
  if(ro-rf!=3||!held)errors++;
  printf("RELAY_BENCH checks=%u errors=%u %s\n",checks,errors,errors?"FAIL":"PASS");return errors?1:0;}
