#include "s81_minimum_hbm.hpp"
#include "VDsromKvRopeMux.h"
#include "verilated.h"
#include <iostream>
#include <cassert>
using namespace dsrom_s81_minimum;
int main(int argc,char**argv){
 if(argc!=2)throw std::runtime_error("actual prior-history directory required");
 VerilatedContext ctx;long cycle=0;
 DsromS81MinimumRuntime r{};r.context=&ctx;r.cycle=[&]{return cycle;};
 VDsromKvRopeMux mux(&ctx,"test_actual_c8_mux");
 auto service=std::make_shared<NativeHbm>(r,"test_actual_hbm");
 service->preload(argv[1]);service->bind(mux);auto p=service->participant();
 auto tick=[&](bool released){
   mux.clk=0;mux.rst_n=released;mux.eval();p.prepare({});
   mux.clk=1;mux.eval();p.rising(released);
   mux.clk=0;mux.eval();p.falling(released);++cycle;ctx.timeInc(1);
 };
 tick(false);tick(false);
 mux.rst_n=1;mux.w_srdy=15;mux.c_srdy=15;mux.p_srdy=15;
 // Each stack writes one actual sector with different nonzero opaque bits.
 mux.w_v=15;mux.w_we=15;mux.w_len=0x1111;mux.w_tag=0x0004000300020001ull;
 for(unsigned s=0;s<4;s++){
   unsigned a=3000000+s;for(unsigned b=0;b<30;b++)if((a>>b)&1)
     mux.w_addr[(s*30+b)/32]|=1u<<((s*30+b)%32);
   mux.w_wstrb[s]=0xffffffffu;
   for(unsigned w=0;w<8;w++)mux.w_wdata[s*8+w]=0x51000000u+256*s+w;
 }
 unsigned accepted=0,committed=0;
 for(unsigned t=0;t<1000;t++){
   if(t>=1000)throw std::runtime_error("native write did not drain");
   mux.clk=0;mux.eval();p.prepare({});
   unsigned a=mux.w_v&mux.w_rdy,d=mux.w_wr_done;
   mux.clk=1;mux.eval();p.rising(true);
   mux.clk=0;mux.eval();p.falling(true);++cycle;
   accepted|=a;committed|=d;mux.w_v&=~a;
   if(accepted==15&&committed==15&&service->drained())break;
 }
 // wr_done is observed before its receiver edge, never fabricated on ready.
 std::cerr<<"write accepted="<<accepted<<" committed="<<committed<<" drained="<<service->drained()<<" cycle="<<cycle<<"\n";assert(accepted==15&&committed==15&&service->drained());
 mux.w_v=15;mux.w_we=0;unsigned got=0;accepted=0;
 for(unsigned t=0;t<1000;t++){
   mux.clk=0;mux.eval();p.prepare({});unsigned a=mux.w_v&mux.w_rdy;
   for(unsigned s=0;s<4;s++)if((mux.w_sv>>s)&1){
     assert(!(got&(1u<<s)));got|=1u<<s;
     for(unsigned w=0;w<8;w++)assert(mux.w_sdata[s*8+w]==0x51000000u+256*s+w);
   }
   mux.clk=1;mux.eval();p.rising(true);
   mux.clk=0;mux.eval();p.falling(true);++cycle;accepted|=a;mux.w_v&=~a;
   if(got==15&&service->drained())break;
 }
 assert(got==15&&accepted==15&&service->drained());
 bool denied=false;try{service->preload(argv[1]);}catch(const std::runtime_error&){denied=true;}
 assert(denied);std::cout<<"PASS_NATIVE_HBM_FOUR_STACKS write_accept=4 native_commit=4 read_return=4 reload_denied=1 cycles="<<cycle<<"\n";
}
