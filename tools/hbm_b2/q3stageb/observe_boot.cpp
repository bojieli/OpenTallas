// Read-only startup measurement against the already compiled final observer.
#include "verilated.h"
#include "Vtb_q3stageb.h"
#include "Vtb_q3stageb___024root.h"
#include <memory>
#include <cstdio>
#include <vector>
int main(int argc,char**argv){
 auto c=std::make_unique<VerilatedContext>();c->threads(1);c->commandArgs(argc,argv);
 auto t=std::make_unique<Vtb_q3stageb>(c.get(),"");bool prevclk=false,prevcv=false;unsigned frames=0;long first=-1,last=-1,desc=-1;std::vector<unsigned> rows;
 while(!c->gotFinish()){
  t->eval();auto*r=t->rootp;bool clk=r->tb_q3stageb__DOT__clk;
  if(!clk&&prevclk){
   unsigned cyc=r->tb_q3stageb__DOT__cyc;bool cv=r->tb_q3stageb__DOT__cv;
   if(cv){++frames;if(first<0)first=cyc;last=cyc;if(!prevcv)rows.push_back(cyc);}
   if(r->tb_q3stageb__DOT__dvc&&desc<0)desc=cyc;
   if(r->tb_q3stageb__DOT__configured){
    std::printf("BOOT_SETUP configured%u first_frame%ld last_frame%ld descriptor%ld frames%u rows%zu from_first%ld\n",cyc,first,last,desc,frames,rows.size(),long(cyc)-first);
    for(size_t j=0;j<rows.size();++j)std::printf("ROW_START %zu %u\n",j,rows[j]);
    t->final();return 0;
   }
   prevcv=cv;
  }
  prevclk=clk;if(!t->eventsPending())break;c->time(t->nextTimeSlot());
 }
 std::fprintf(stderr,"BOOT_SETUP MISSING\n");return 1;
}
