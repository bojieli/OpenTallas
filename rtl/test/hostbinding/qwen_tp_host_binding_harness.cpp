#include "Vot_qwen_tp_host_binding.h"
#include <array>
#include <cstdint>
#include <cstdio>
#include <stdexcept>
static void check(bool v,const char* msg) { if(!v) throw std::runtime_error(msg); }
static uint64_t descriptor(unsigned kind,unsigned base,unsigned row) {
 return kind | (uint64_t(7)<<2) | (uint64_t(2)<<10) |
        (uint64_t(row>>16)<<18) | (uint64_t(base)<<32) | (uint64_t(row&65535)<<48);
}
static void run(bool tie) {
 Vot_qwen_tp_host_binding t;
 uint32_t vm[2][256][16]={};
 for(unsigned d=0;d<2;d++) for(unsigned a=7;a<9;a++) for(unsigned l=0;l<16;l++)
   vm[d][a][l]=d ? 0x40000000 : 0x3f800000; // exact 1 + 2 = 3
 unsigned launches[2]={},reads[2]={},writes[2]={},pending[2]={};
 t.clk=0;t.rst_n=0;t.start=0;t.token=150000;t.pos=17;
 t.core_done=0;t.core_fault=0;t.core_next_token=0;t.core_next_val=0;
 for(auto &q:t.desc_q) q=0;
 for(auto &q:t.vm_rq) q=0;
 for(unsigned cycle=0;cycle<1000;cycle++) {
   t.clk=0;t.eval();
   auto dre=t.desc_re;auto da=t.desc_addr;auto re=t.vm_re;auto ra=t.vm_raddr;
   auto we=t.vm_we;auto wa=t.vm_waddr;auto cs=t.core_start;
   std::array<uint32_t,32> w{},q{};
   for(unsigned i=0;i<32;i++) w[i]=t.vm_wdata[i];
   uint64_t dq[2]={};
   for(unsigned d=0;d<2;d++) {
     if((dre>>d)&1) {
       unsigned a=(da>>(d*6))&63;check(a<2,"descriptor order");
       dq[d]=descriptor(a?2:1,a?31:9,d?131072:70000);
     }
     if((re>>d)&1) {
       unsigned a=(ra>>(d*8))&255;check(a==7+reads[d]++,"VM read order");
       for(unsigned l=0;l<16;l++) q[d*16+l]=vm[d][a][l];
     }
     if((cs>>d)&1) {
       check(((t.prog_base>>(d*12))&4095)==(launches[d]?31:9),"program base");
       check(((t.core_token>>(d*18))&262143)==150000,"token width");
       check(((t.core_pos>>(d*18))&262143)==17,"position");
       launches[d]++;pending[d]=3+d; // unequal core latencies
     }
   }
   t.clk=1;t.eval();
   // All sampled inputs remain unchanged until the edge has evaluated.
   for(unsigned d=0;d<2;d++) {
     if((dre>>d)&1) {t.desc_q[d*2]=dq[d];t.desc_q[d*2+1]=dq[d]>>32;}
     if((re>>d)&1) for(unsigned l=0;l<16;l++) t.vm_rq[d*16+l]=q[d*16+l];
     if((we>>d)&1) {
       unsigned a=(wa>>(d*8))&255;check(a==7+writes[d]++,"VM write order");
       for(unsigned l=0;l<16;l++) {check(w[d*16+l]==0x40400000,"rank-order FP32 sum");vm[d][a][l]=w[d*16+l];}
     }
   }
   t.core_done=0;
   for(unsigned d=0;d<2;d++) if(pending[d] && --pending[d]==0) t.core_done|=1<<d;
   t.core_next_token=uint64_t(11)|(uint64_t(23)<<18);
   t.core_next_val=uint64_t(0x40800000)|(uint64_t(tie?0x40800000:0x40a00000)<<32);
   t.rst_n=cycle>=1;t.start=cycle==2;t.eval();
   check(!t.seq_fault && !t.coll_fault,"RTL fault");
   if(t.done==3) {
     unsigned expected=tie?70011:131095;
     for(unsigned d=0;d<2;d++) {
       check(launches[d]==2 && reads[d]==2 && writes[d]==2,"transaction counts");
       check(((t.next_token>>(d*18))&262143)==expected,"fullshape argmax rank/tie order");
     }
     std::printf("PASS tie=%d cycles=%u token=%u stalls=%u\n",tie,cycle,expected,t.link_stalls);return;
   }
 }
 throw std::runtime_error("timeout");
}
int main() {run(false);run(true);}
