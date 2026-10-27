#include "Vtb.h"
#include "Vtb___024root.h"
#include "verilated.h"
#include <cstdio>
#include <cstring>
static double g_t=0;
double sc_time_stamp(){return g_t;}
int main(int argc,char**argv){
 Verilated::commandArgs(argc,argv);FILE*fp=nullptr;
 for(int i=1;i<argc;++i)if(!std::strncmp(argv[i],"+PINLOG=",8))fp=std::fopen(argv[i]+8,"w");
 Vtb*t=new Vtb;t->ck=0;
 while(!Verilated::gotFinish()){
  t->ck=!t->ck;t->eval();
  if(t->ck&&fp){auto*r=t->rootp;int hr=(r->tb__DOT__hr_q[14]>>4)&1;int go=r->tb__DOT__u__DOT__hw[0]&1;
   int xf=(r->tb__DOT__hr_q[0]>>1)&1;
   if(hr||go||xf)std::fprintf(fp,"%u %d %d %d\n",r->tb__DOT__cyc,hr,go,xf);
  }
  g_t+=0.5;
 }
 t->final();if(fp)std::fclose(fp);delete t;return 0;
}
