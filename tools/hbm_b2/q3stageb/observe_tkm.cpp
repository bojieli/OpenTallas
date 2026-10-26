// Diagnostic read-only observer for the existing no-ID current-view model.
// Link against immutable noidpr_r2 archives in a new output directory; this
// does not rebuild or modify its RTL, objects, binary, or running processes.
#include "verilated.h"
#include "Vtb_hbm_tkm_bound_tkx_ft21.h"
#include "Vtb_hbm_tkm_bound_tkx_ft21___024root.h"
#include <memory>
#include <cstdio>
int main(int argc,char**argv){
 auto context=std::make_unique<VerilatedContext>();context->threads(1);context->commandArgs(argc,argv);
 auto top=std::make_unique<Vtb_hbm_tkm_bound_tkx_ft21>(context.get(),"");
 bool prevclk=false,prevsend=false,prevwv=false,prevdone=false;unsigned long cyc=0;long start=-1;
 while(!context->gotFinish()){
  top->eval();auto*r=top->rootp;bool clk=r->tb_hbm_tkm_bound_tkx_ft21__DOT__clk;
  if(clk&&!prevclk)++cyc;
  if(!clk&&prevclk){
   bool send=r->tb_hbm_tkm_bound_tkx_ft21__DOT__send_start;
   unsigned control=r->tb_hbm_tkm_bound_tkx_ft21__DOT__bound__DOT__returned__DOT__c[1];
   bool wv=(control>>2)&1,done=(control>>1)&1;
   if(send&&!prevsend){start=long(cyc);std::printf("OBS RAW_START cycle%lu\n",cyc);}
   if(wv&&!prevwv)std::printf("OBS RETURN_WRITE cycle%lu raw_age%ld\n",cyc,long(cyc)-start);
   if(done&&!prevdone)std::printf("OBS RETURN_DONE cycle%lu raw_age%ld\n",cyc,long(cyc)-start);
   prevsend=send;prevwv=wv;prevdone=done;
  }
  prevclk=clk;if(!top->eventsPending())break;context->time(top->nextTimeSlot());
 }
 top->final();context->statsPrintSummary();return 0;
}
