#include "verilated.h"
#include "Vtb_dsfd_vm_static_core.h"
#include "Vtb_dsfd_vm_static_core___024root.h"
#include "Vtb_dsfd_vm_static_core_dsfd_vm_static_slice128_suhc__pi5.h"
#include <map>
int main(int argc,char **argv) {
 auto ctx=std::make_unique<VerilatedContext>(); ctx->threads(1);ctx->commandArgs(argc,argv);
 auto top=std::make_unique<Vtb_dsfd_vm_static_core>(ctx.get(),"");
 unsigned actual_total=0,expected_total=0,bad=0,compared_cycles=0;
 auto get14=[](const auto &words,int bit){uint64_t x=words[bit/32]; if(bit%32>18)x|=uint64_t(words[bit/32+1])<<32; return unsigned((x>>(bit%32))&0x3fff);};
 while(!ctx->gotFinish()) {
  if(ctx->time()%834==417 && top->rootp->tb_dsfd_vm_static_core__DOT__rss) {
   auto *r=top->rootp; int cy=int(r->tb_dsfd_vm_static_core__DOT__cy);
   // Fixed specification: request pin P -> macro read edge P+7 -> output P+16.
   // External expected output table therefore indexed at cy-7+16, never learned.
   int due=cy+9; std::map<unsigned,unsigned> actual,expected;
   auto expect_row=[&](unsigned row){for(unsigned slice=0;slice<4;++slice)++expected[row*4+slice];};
   if(due>=0 && due<40000) {
    for(unsigned port=0;port<18;++port)if((r->tb_dsfd_vm_static_core__DOT__rv_exp[due]>>port)&1)expect_row(get14(r->tb_dsfd_vm_static_core__DOT__rr_exp[due],14*port));
    for(unsigned port=0;port<20;++port)if((r->tb_dsfd_vm_static_core__DOT__mx_exp[due]>>port)&1)expect_row(get14(r->tb_dsfd_vm_static_core__DOT__mx_row[due],14*port));
    if(r->tb_dsfd_vm_static_core__DOT__cr_exp[due])expect_row(r->tb_dsfd_vm_static_core__DOT__cr_row[due]);
    if(r->tb_dsfd_vm_static_core__DOT__pq_exp[due])for(unsigned q=0;q<4;++q)expect_row(r->tb_dsfd_vm_static_core__DOT__pq_row[due]+q);
   }
auto *s0=r->__PVT__tb_dsfd_vm_static_core__DOT__dut__DOT__u_mem__DOT__slice__BRA__0__KET____DOT__u_slice;
if(s0->__PVT__bank__BRA__0__KET____DOT__u_bank__DOT__rvq){unsigned a=s0->__PVT__bank__BRA__0__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(0^((a&7)<<2)); ++actual[row*4+0];}
if(s0->__PVT__bank__BRA__1__KET____DOT__u_bank__DOT__rvq){unsigned a=s0->__PVT__bank__BRA__1__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(1^((a&7)<<2)); ++actual[row*4+0];}
if(s0->__PVT__bank__BRA__2__KET____DOT__u_bank__DOT__rvq){unsigned a=s0->__PVT__bank__BRA__2__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(2^((a&7)<<2)); ++actual[row*4+0];}
if(s0->__PVT__bank__BRA__3__KET____DOT__u_bank__DOT__rvq){unsigned a=s0->__PVT__bank__BRA__3__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(3^((a&7)<<2)); ++actual[row*4+0];}
if(s0->__PVT__bank__BRA__4__KET____DOT__u_bank__DOT__rvq){unsigned a=s0->__PVT__bank__BRA__4__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(4^((a&7)<<2)); ++actual[row*4+0];}
if(s0->__PVT__bank__BRA__5__KET____DOT__u_bank__DOT__rvq){unsigned a=s0->__PVT__bank__BRA__5__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(5^((a&7)<<2)); ++actual[row*4+0];}
if(s0->__PVT__bank__BRA__6__KET____DOT__u_bank__DOT__rvq){unsigned a=s0->__PVT__bank__BRA__6__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(6^((a&7)<<2)); ++actual[row*4+0];}
if(s0->__PVT__bank__BRA__7__KET____DOT__u_bank__DOT__rvq){unsigned a=s0->__PVT__bank__BRA__7__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(7^((a&7)<<2)); ++actual[row*4+0];}
if(s0->__PVT__bank__BRA__8__KET____DOT__u_bank__DOT__rvq){unsigned a=s0->__PVT__bank__BRA__8__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(8^((a&7)<<2)); ++actual[row*4+0];}
if(s0->__PVT__bank__BRA__9__KET____DOT__u_bank__DOT__rvq){unsigned a=s0->__PVT__bank__BRA__9__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(9^((a&7)<<2)); ++actual[row*4+0];}
if(s0->__PVT__bank__BRA__10__KET____DOT__u_bank__DOT__rvq){unsigned a=s0->__PVT__bank__BRA__10__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(10^((a&7)<<2)); ++actual[row*4+0];}
if(s0->__PVT__bank__BRA__11__KET____DOT__u_bank__DOT__rvq){unsigned a=s0->__PVT__bank__BRA__11__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(11^((a&7)<<2)); ++actual[row*4+0];}
if(s0->__PVT__bank__BRA__12__KET____DOT__u_bank__DOT__rvq){unsigned a=s0->__PVT__bank__BRA__12__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(12^((a&7)<<2)); ++actual[row*4+0];}
if(s0->__PVT__bank__BRA__13__KET____DOT__u_bank__DOT__rvq){unsigned a=s0->__PVT__bank__BRA__13__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(13^((a&7)<<2)); ++actual[row*4+0];}
if(s0->__PVT__bank__BRA__14__KET____DOT__u_bank__DOT__rvq){unsigned a=s0->__PVT__bank__BRA__14__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(14^((a&7)<<2)); ++actual[row*4+0];}
if(s0->__PVT__bank__BRA__15__KET____DOT__u_bank__DOT__rvq){unsigned a=s0->__PVT__bank__BRA__15__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(15^((a&7)<<2)); ++actual[row*4+0];}
if(s0->__PVT__bank__BRA__16__KET____DOT__u_bank__DOT__rvq){unsigned a=s0->__PVT__bank__BRA__16__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(16^((a&7)<<2)); ++actual[row*4+0];}
if(s0->__PVT__bank__BRA__17__KET____DOT__u_bank__DOT__rvq){unsigned a=s0->__PVT__bank__BRA__17__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(17^((a&7)<<2)); ++actual[row*4+0];}
if(s0->__PVT__bank__BRA__18__KET____DOT__u_bank__DOT__rvq){unsigned a=s0->__PVT__bank__BRA__18__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(18^((a&7)<<2)); ++actual[row*4+0];}
if(s0->__PVT__bank__BRA__19__KET____DOT__u_bank__DOT__rvq){unsigned a=s0->__PVT__bank__BRA__19__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(19^((a&7)<<2)); ++actual[row*4+0];}
if(s0->__PVT__bank__BRA__20__KET____DOT__u_bank__DOT__rvq){unsigned a=s0->__PVT__bank__BRA__20__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(20^((a&7)<<2)); ++actual[row*4+0];}
if(s0->__PVT__bank__BRA__21__KET____DOT__u_bank__DOT__rvq){unsigned a=s0->__PVT__bank__BRA__21__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(21^((a&7)<<2)); ++actual[row*4+0];}
if(s0->__PVT__bank__BRA__22__KET____DOT__u_bank__DOT__rvq){unsigned a=s0->__PVT__bank__BRA__22__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(22^((a&7)<<2)); ++actual[row*4+0];}
if(s0->__PVT__bank__BRA__23__KET____DOT__u_bank__DOT__rvq){unsigned a=s0->__PVT__bank__BRA__23__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(23^((a&7)<<2)); ++actual[row*4+0];}
if(s0->__PVT__bank__BRA__24__KET____DOT__u_bank__DOT__rvq){unsigned a=s0->__PVT__bank__BRA__24__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(24^((a&7)<<2)); ++actual[row*4+0];}
if(s0->__PVT__bank__BRA__25__KET____DOT__u_bank__DOT__rvq){unsigned a=s0->__PVT__bank__BRA__25__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(25^((a&7)<<2)); ++actual[row*4+0];}
if(s0->__PVT__bank__BRA__26__KET____DOT__u_bank__DOT__rvq){unsigned a=s0->__PVT__bank__BRA__26__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(26^((a&7)<<2)); ++actual[row*4+0];}
if(s0->__PVT__bank__BRA__27__KET____DOT__u_bank__DOT__rvq){unsigned a=s0->__PVT__bank__BRA__27__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(27^((a&7)<<2)); ++actual[row*4+0];}
if(s0->__PVT__bank__BRA__28__KET____DOT__u_bank__DOT__rvq){unsigned a=s0->__PVT__bank__BRA__28__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(28^((a&7)<<2)); ++actual[row*4+0];}
if(s0->__PVT__bank__BRA__29__KET____DOT__u_bank__DOT__rvq){unsigned a=s0->__PVT__bank__BRA__29__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(29^((a&7)<<2)); ++actual[row*4+0];}
if(s0->__PVT__bank__BRA__30__KET____DOT__u_bank__DOT__rvq){unsigned a=s0->__PVT__bank__BRA__30__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(30^((a&7)<<2)); ++actual[row*4+0];}
if(s0->__PVT__bank__BRA__31__KET____DOT__u_bank__DOT__rvq){unsigned a=s0->__PVT__bank__BRA__31__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(31^((a&7)<<2)); ++actual[row*4+0];}
auto *s1=r->__PVT__tb_dsfd_vm_static_core__DOT__dut__DOT__u_mem__DOT__slice__BRA__1__KET____DOT__u_slice;
if(s1->__PVT__bank__BRA__0__KET____DOT__u_bank__DOT__rvq){unsigned a=s1->__PVT__bank__BRA__0__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(0^((a&7)<<2)); ++actual[row*4+1];}
if(s1->__PVT__bank__BRA__1__KET____DOT__u_bank__DOT__rvq){unsigned a=s1->__PVT__bank__BRA__1__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(1^((a&7)<<2)); ++actual[row*4+1];}
if(s1->__PVT__bank__BRA__2__KET____DOT__u_bank__DOT__rvq){unsigned a=s1->__PVT__bank__BRA__2__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(2^((a&7)<<2)); ++actual[row*4+1];}
if(s1->__PVT__bank__BRA__3__KET____DOT__u_bank__DOT__rvq){unsigned a=s1->__PVT__bank__BRA__3__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(3^((a&7)<<2)); ++actual[row*4+1];}
if(s1->__PVT__bank__BRA__4__KET____DOT__u_bank__DOT__rvq){unsigned a=s1->__PVT__bank__BRA__4__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(4^((a&7)<<2)); ++actual[row*4+1];}
if(s1->__PVT__bank__BRA__5__KET____DOT__u_bank__DOT__rvq){unsigned a=s1->__PVT__bank__BRA__5__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(5^((a&7)<<2)); ++actual[row*4+1];}
if(s1->__PVT__bank__BRA__6__KET____DOT__u_bank__DOT__rvq){unsigned a=s1->__PVT__bank__BRA__6__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(6^((a&7)<<2)); ++actual[row*4+1];}
if(s1->__PVT__bank__BRA__7__KET____DOT__u_bank__DOT__rvq){unsigned a=s1->__PVT__bank__BRA__7__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(7^((a&7)<<2)); ++actual[row*4+1];}
if(s1->__PVT__bank__BRA__8__KET____DOT__u_bank__DOT__rvq){unsigned a=s1->__PVT__bank__BRA__8__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(8^((a&7)<<2)); ++actual[row*4+1];}
if(s1->__PVT__bank__BRA__9__KET____DOT__u_bank__DOT__rvq){unsigned a=s1->__PVT__bank__BRA__9__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(9^((a&7)<<2)); ++actual[row*4+1];}
if(s1->__PVT__bank__BRA__10__KET____DOT__u_bank__DOT__rvq){unsigned a=s1->__PVT__bank__BRA__10__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(10^((a&7)<<2)); ++actual[row*4+1];}
if(s1->__PVT__bank__BRA__11__KET____DOT__u_bank__DOT__rvq){unsigned a=s1->__PVT__bank__BRA__11__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(11^((a&7)<<2)); ++actual[row*4+1];}
if(s1->__PVT__bank__BRA__12__KET____DOT__u_bank__DOT__rvq){unsigned a=s1->__PVT__bank__BRA__12__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(12^((a&7)<<2)); ++actual[row*4+1];}
if(s1->__PVT__bank__BRA__13__KET____DOT__u_bank__DOT__rvq){unsigned a=s1->__PVT__bank__BRA__13__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(13^((a&7)<<2)); ++actual[row*4+1];}
if(s1->__PVT__bank__BRA__14__KET____DOT__u_bank__DOT__rvq){unsigned a=s1->__PVT__bank__BRA__14__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(14^((a&7)<<2)); ++actual[row*4+1];}
if(s1->__PVT__bank__BRA__15__KET____DOT__u_bank__DOT__rvq){unsigned a=s1->__PVT__bank__BRA__15__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(15^((a&7)<<2)); ++actual[row*4+1];}
if(s1->__PVT__bank__BRA__16__KET____DOT__u_bank__DOT__rvq){unsigned a=s1->__PVT__bank__BRA__16__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(16^((a&7)<<2)); ++actual[row*4+1];}
if(s1->__PVT__bank__BRA__17__KET____DOT__u_bank__DOT__rvq){unsigned a=s1->__PVT__bank__BRA__17__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(17^((a&7)<<2)); ++actual[row*4+1];}
if(s1->__PVT__bank__BRA__18__KET____DOT__u_bank__DOT__rvq){unsigned a=s1->__PVT__bank__BRA__18__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(18^((a&7)<<2)); ++actual[row*4+1];}
if(s1->__PVT__bank__BRA__19__KET____DOT__u_bank__DOT__rvq){unsigned a=s1->__PVT__bank__BRA__19__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(19^((a&7)<<2)); ++actual[row*4+1];}
if(s1->__PVT__bank__BRA__20__KET____DOT__u_bank__DOT__rvq){unsigned a=s1->__PVT__bank__BRA__20__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(20^((a&7)<<2)); ++actual[row*4+1];}
if(s1->__PVT__bank__BRA__21__KET____DOT__u_bank__DOT__rvq){unsigned a=s1->__PVT__bank__BRA__21__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(21^((a&7)<<2)); ++actual[row*4+1];}
if(s1->__PVT__bank__BRA__22__KET____DOT__u_bank__DOT__rvq){unsigned a=s1->__PVT__bank__BRA__22__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(22^((a&7)<<2)); ++actual[row*4+1];}
if(s1->__PVT__bank__BRA__23__KET____DOT__u_bank__DOT__rvq){unsigned a=s1->__PVT__bank__BRA__23__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(23^((a&7)<<2)); ++actual[row*4+1];}
if(s1->__PVT__bank__BRA__24__KET____DOT__u_bank__DOT__rvq){unsigned a=s1->__PVT__bank__BRA__24__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(24^((a&7)<<2)); ++actual[row*4+1];}
if(s1->__PVT__bank__BRA__25__KET____DOT__u_bank__DOT__rvq){unsigned a=s1->__PVT__bank__BRA__25__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(25^((a&7)<<2)); ++actual[row*4+1];}
if(s1->__PVT__bank__BRA__26__KET____DOT__u_bank__DOT__rvq){unsigned a=s1->__PVT__bank__BRA__26__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(26^((a&7)<<2)); ++actual[row*4+1];}
if(s1->__PVT__bank__BRA__27__KET____DOT__u_bank__DOT__rvq){unsigned a=s1->__PVT__bank__BRA__27__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(27^((a&7)<<2)); ++actual[row*4+1];}
if(s1->__PVT__bank__BRA__28__KET____DOT__u_bank__DOT__rvq){unsigned a=s1->__PVT__bank__BRA__28__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(28^((a&7)<<2)); ++actual[row*4+1];}
if(s1->__PVT__bank__BRA__29__KET____DOT__u_bank__DOT__rvq){unsigned a=s1->__PVT__bank__BRA__29__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(29^((a&7)<<2)); ++actual[row*4+1];}
if(s1->__PVT__bank__BRA__30__KET____DOT__u_bank__DOT__rvq){unsigned a=s1->__PVT__bank__BRA__30__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(30^((a&7)<<2)); ++actual[row*4+1];}
if(s1->__PVT__bank__BRA__31__KET____DOT__u_bank__DOT__rvq){unsigned a=s1->__PVT__bank__BRA__31__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(31^((a&7)<<2)); ++actual[row*4+1];}
auto *s2=r->__PVT__tb_dsfd_vm_static_core__DOT__dut__DOT__u_mem__DOT__slice__BRA__2__KET____DOT__u_slice;
if(s2->__PVT__bank__BRA__0__KET____DOT__u_bank__DOT__rvq){unsigned a=s2->__PVT__bank__BRA__0__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(0^((a&7)<<2)); ++actual[row*4+2];}
if(s2->__PVT__bank__BRA__1__KET____DOT__u_bank__DOT__rvq){unsigned a=s2->__PVT__bank__BRA__1__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(1^((a&7)<<2)); ++actual[row*4+2];}
if(s2->__PVT__bank__BRA__2__KET____DOT__u_bank__DOT__rvq){unsigned a=s2->__PVT__bank__BRA__2__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(2^((a&7)<<2)); ++actual[row*4+2];}
if(s2->__PVT__bank__BRA__3__KET____DOT__u_bank__DOT__rvq){unsigned a=s2->__PVT__bank__BRA__3__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(3^((a&7)<<2)); ++actual[row*4+2];}
if(s2->__PVT__bank__BRA__4__KET____DOT__u_bank__DOT__rvq){unsigned a=s2->__PVT__bank__BRA__4__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(4^((a&7)<<2)); ++actual[row*4+2];}
if(s2->__PVT__bank__BRA__5__KET____DOT__u_bank__DOT__rvq){unsigned a=s2->__PVT__bank__BRA__5__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(5^((a&7)<<2)); ++actual[row*4+2];}
if(s2->__PVT__bank__BRA__6__KET____DOT__u_bank__DOT__rvq){unsigned a=s2->__PVT__bank__BRA__6__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(6^((a&7)<<2)); ++actual[row*4+2];}
if(s2->__PVT__bank__BRA__7__KET____DOT__u_bank__DOT__rvq){unsigned a=s2->__PVT__bank__BRA__7__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(7^((a&7)<<2)); ++actual[row*4+2];}
if(s2->__PVT__bank__BRA__8__KET____DOT__u_bank__DOT__rvq){unsigned a=s2->__PVT__bank__BRA__8__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(8^((a&7)<<2)); ++actual[row*4+2];}
if(s2->__PVT__bank__BRA__9__KET____DOT__u_bank__DOT__rvq){unsigned a=s2->__PVT__bank__BRA__9__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(9^((a&7)<<2)); ++actual[row*4+2];}
if(s2->__PVT__bank__BRA__10__KET____DOT__u_bank__DOT__rvq){unsigned a=s2->__PVT__bank__BRA__10__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(10^((a&7)<<2)); ++actual[row*4+2];}
if(s2->__PVT__bank__BRA__11__KET____DOT__u_bank__DOT__rvq){unsigned a=s2->__PVT__bank__BRA__11__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(11^((a&7)<<2)); ++actual[row*4+2];}
if(s2->__PVT__bank__BRA__12__KET____DOT__u_bank__DOT__rvq){unsigned a=s2->__PVT__bank__BRA__12__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(12^((a&7)<<2)); ++actual[row*4+2];}
if(s2->__PVT__bank__BRA__13__KET____DOT__u_bank__DOT__rvq){unsigned a=s2->__PVT__bank__BRA__13__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(13^((a&7)<<2)); ++actual[row*4+2];}
if(s2->__PVT__bank__BRA__14__KET____DOT__u_bank__DOT__rvq){unsigned a=s2->__PVT__bank__BRA__14__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(14^((a&7)<<2)); ++actual[row*4+2];}
if(s2->__PVT__bank__BRA__15__KET____DOT__u_bank__DOT__rvq){unsigned a=s2->__PVT__bank__BRA__15__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(15^((a&7)<<2)); ++actual[row*4+2];}
if(s2->__PVT__bank__BRA__16__KET____DOT__u_bank__DOT__rvq){unsigned a=s2->__PVT__bank__BRA__16__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(16^((a&7)<<2)); ++actual[row*4+2];}
if(s2->__PVT__bank__BRA__17__KET____DOT__u_bank__DOT__rvq){unsigned a=s2->__PVT__bank__BRA__17__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(17^((a&7)<<2)); ++actual[row*4+2];}
if(s2->__PVT__bank__BRA__18__KET____DOT__u_bank__DOT__rvq){unsigned a=s2->__PVT__bank__BRA__18__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(18^((a&7)<<2)); ++actual[row*4+2];}
if(s2->__PVT__bank__BRA__19__KET____DOT__u_bank__DOT__rvq){unsigned a=s2->__PVT__bank__BRA__19__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(19^((a&7)<<2)); ++actual[row*4+2];}
if(s2->__PVT__bank__BRA__20__KET____DOT__u_bank__DOT__rvq){unsigned a=s2->__PVT__bank__BRA__20__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(20^((a&7)<<2)); ++actual[row*4+2];}
if(s2->__PVT__bank__BRA__21__KET____DOT__u_bank__DOT__rvq){unsigned a=s2->__PVT__bank__BRA__21__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(21^((a&7)<<2)); ++actual[row*4+2];}
if(s2->__PVT__bank__BRA__22__KET____DOT__u_bank__DOT__rvq){unsigned a=s2->__PVT__bank__BRA__22__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(22^((a&7)<<2)); ++actual[row*4+2];}
if(s2->__PVT__bank__BRA__23__KET____DOT__u_bank__DOT__rvq){unsigned a=s2->__PVT__bank__BRA__23__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(23^((a&7)<<2)); ++actual[row*4+2];}
if(s2->__PVT__bank__BRA__24__KET____DOT__u_bank__DOT__rvq){unsigned a=s2->__PVT__bank__BRA__24__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(24^((a&7)<<2)); ++actual[row*4+2];}
if(s2->__PVT__bank__BRA__25__KET____DOT__u_bank__DOT__rvq){unsigned a=s2->__PVT__bank__BRA__25__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(25^((a&7)<<2)); ++actual[row*4+2];}
if(s2->__PVT__bank__BRA__26__KET____DOT__u_bank__DOT__rvq){unsigned a=s2->__PVT__bank__BRA__26__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(26^((a&7)<<2)); ++actual[row*4+2];}
if(s2->__PVT__bank__BRA__27__KET____DOT__u_bank__DOT__rvq){unsigned a=s2->__PVT__bank__BRA__27__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(27^((a&7)<<2)); ++actual[row*4+2];}
if(s2->__PVT__bank__BRA__28__KET____DOT__u_bank__DOT__rvq){unsigned a=s2->__PVT__bank__BRA__28__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(28^((a&7)<<2)); ++actual[row*4+2];}
if(s2->__PVT__bank__BRA__29__KET____DOT__u_bank__DOT__rvq){unsigned a=s2->__PVT__bank__BRA__29__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(29^((a&7)<<2)); ++actual[row*4+2];}
if(s2->__PVT__bank__BRA__30__KET____DOT__u_bank__DOT__rvq){unsigned a=s2->__PVT__bank__BRA__30__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(30^((a&7)<<2)); ++actual[row*4+2];}
if(s2->__PVT__bank__BRA__31__KET____DOT__u_bank__DOT__rvq){unsigned a=s2->__PVT__bank__BRA__31__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(31^((a&7)<<2)); ++actual[row*4+2];}
auto *s3=r->__PVT__tb_dsfd_vm_static_core__DOT__dut__DOT__u_mem__DOT__slice__BRA__3__KET____DOT__u_slice;
if(s3->__PVT__bank__BRA__0__KET____DOT__u_bank__DOT__rvq){unsigned a=s3->__PVT__bank__BRA__0__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(0^((a&7)<<2)); ++actual[row*4+3];}
if(s3->__PVT__bank__BRA__1__KET____DOT__u_bank__DOT__rvq){unsigned a=s3->__PVT__bank__BRA__1__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(1^((a&7)<<2)); ++actual[row*4+3];}
if(s3->__PVT__bank__BRA__2__KET____DOT__u_bank__DOT__rvq){unsigned a=s3->__PVT__bank__BRA__2__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(2^((a&7)<<2)); ++actual[row*4+3];}
if(s3->__PVT__bank__BRA__3__KET____DOT__u_bank__DOT__rvq){unsigned a=s3->__PVT__bank__BRA__3__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(3^((a&7)<<2)); ++actual[row*4+3];}
if(s3->__PVT__bank__BRA__4__KET____DOT__u_bank__DOT__rvq){unsigned a=s3->__PVT__bank__BRA__4__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(4^((a&7)<<2)); ++actual[row*4+3];}
if(s3->__PVT__bank__BRA__5__KET____DOT__u_bank__DOT__rvq){unsigned a=s3->__PVT__bank__BRA__5__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(5^((a&7)<<2)); ++actual[row*4+3];}
if(s3->__PVT__bank__BRA__6__KET____DOT__u_bank__DOT__rvq){unsigned a=s3->__PVT__bank__BRA__6__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(6^((a&7)<<2)); ++actual[row*4+3];}
if(s3->__PVT__bank__BRA__7__KET____DOT__u_bank__DOT__rvq){unsigned a=s3->__PVT__bank__BRA__7__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(7^((a&7)<<2)); ++actual[row*4+3];}
if(s3->__PVT__bank__BRA__8__KET____DOT__u_bank__DOT__rvq){unsigned a=s3->__PVT__bank__BRA__8__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(8^((a&7)<<2)); ++actual[row*4+3];}
if(s3->__PVT__bank__BRA__9__KET____DOT__u_bank__DOT__rvq){unsigned a=s3->__PVT__bank__BRA__9__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(9^((a&7)<<2)); ++actual[row*4+3];}
if(s3->__PVT__bank__BRA__10__KET____DOT__u_bank__DOT__rvq){unsigned a=s3->__PVT__bank__BRA__10__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(10^((a&7)<<2)); ++actual[row*4+3];}
if(s3->__PVT__bank__BRA__11__KET____DOT__u_bank__DOT__rvq){unsigned a=s3->__PVT__bank__BRA__11__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(11^((a&7)<<2)); ++actual[row*4+3];}
if(s3->__PVT__bank__BRA__12__KET____DOT__u_bank__DOT__rvq){unsigned a=s3->__PVT__bank__BRA__12__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(12^((a&7)<<2)); ++actual[row*4+3];}
if(s3->__PVT__bank__BRA__13__KET____DOT__u_bank__DOT__rvq){unsigned a=s3->__PVT__bank__BRA__13__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(13^((a&7)<<2)); ++actual[row*4+3];}
if(s3->__PVT__bank__BRA__14__KET____DOT__u_bank__DOT__rvq){unsigned a=s3->__PVT__bank__BRA__14__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(14^((a&7)<<2)); ++actual[row*4+3];}
if(s3->__PVT__bank__BRA__15__KET____DOT__u_bank__DOT__rvq){unsigned a=s3->__PVT__bank__BRA__15__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(15^((a&7)<<2)); ++actual[row*4+3];}
if(s3->__PVT__bank__BRA__16__KET____DOT__u_bank__DOT__rvq){unsigned a=s3->__PVT__bank__BRA__16__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(16^((a&7)<<2)); ++actual[row*4+3];}
if(s3->__PVT__bank__BRA__17__KET____DOT__u_bank__DOT__rvq){unsigned a=s3->__PVT__bank__BRA__17__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(17^((a&7)<<2)); ++actual[row*4+3];}
if(s3->__PVT__bank__BRA__18__KET____DOT__u_bank__DOT__rvq){unsigned a=s3->__PVT__bank__BRA__18__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(18^((a&7)<<2)); ++actual[row*4+3];}
if(s3->__PVT__bank__BRA__19__KET____DOT__u_bank__DOT__rvq){unsigned a=s3->__PVT__bank__BRA__19__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(19^((a&7)<<2)); ++actual[row*4+3];}
if(s3->__PVT__bank__BRA__20__KET____DOT__u_bank__DOT__rvq){unsigned a=s3->__PVT__bank__BRA__20__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(20^((a&7)<<2)); ++actual[row*4+3];}
if(s3->__PVT__bank__BRA__21__KET____DOT__u_bank__DOT__rvq){unsigned a=s3->__PVT__bank__BRA__21__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(21^((a&7)<<2)); ++actual[row*4+3];}
if(s3->__PVT__bank__BRA__22__KET____DOT__u_bank__DOT__rvq){unsigned a=s3->__PVT__bank__BRA__22__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(22^((a&7)<<2)); ++actual[row*4+3];}
if(s3->__PVT__bank__BRA__23__KET____DOT__u_bank__DOT__rvq){unsigned a=s3->__PVT__bank__BRA__23__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(23^((a&7)<<2)); ++actual[row*4+3];}
if(s3->__PVT__bank__BRA__24__KET____DOT__u_bank__DOT__rvq){unsigned a=s3->__PVT__bank__BRA__24__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(24^((a&7)<<2)); ++actual[row*4+3];}
if(s3->__PVT__bank__BRA__25__KET____DOT__u_bank__DOT__rvq){unsigned a=s3->__PVT__bank__BRA__25__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(25^((a&7)<<2)); ++actual[row*4+3];}
if(s3->__PVT__bank__BRA__26__KET____DOT__u_bank__DOT__rvq){unsigned a=s3->__PVT__bank__BRA__26__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(26^((a&7)<<2)); ++actual[row*4+3];}
if(s3->__PVT__bank__BRA__27__KET____DOT__u_bank__DOT__rvq){unsigned a=s3->__PVT__bank__BRA__27__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(27^((a&7)<<2)); ++actual[row*4+3];}
if(s3->__PVT__bank__BRA__28__KET____DOT__u_bank__DOT__rvq){unsigned a=s3->__PVT__bank__BRA__28__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(28^((a&7)<<2)); ++actual[row*4+3];}
if(s3->__PVT__bank__BRA__29__KET____DOT__u_bank__DOT__rvq){unsigned a=s3->__PVT__bank__BRA__29__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(29^((a&7)<<2)); ++actual[row*4+3];}
if(s3->__PVT__bank__BRA__30__KET____DOT__u_bank__DOT__rvq){unsigned a=s3->__PVT__bank__BRA__30__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(30^((a&7)<<2)); ++actual[row*4+3];}
if(s3->__PVT__bank__BRA__31__KET____DOT__u_bank__DOT__rvq){unsigned a=s3->__PVT__bank__BRA__31__KET____DOT__u_bank__DOT__raq; unsigned row=(a<<5)|(31^((a&7)<<2)); ++actual[row*4+3];}

   for(auto [key,count]:actual)actual_total+=count;
   for(auto [key,count]:expected)expected_total+=count;
   if(!actual.empty()||!expected.empty())++compared_cycles;
   if(actual!=expected){++bad;if(bad<=8)printf("READ_FIXED_FAIL cy=%d due=%d actual_keys=%zu expected_keys=%zu\n",cy,due,actual.size(),expected.size());}
  }
  top->eval();if(!top->eventsPending())break;ctx->time(top->nextTimeSlot());
 }
 top->final();
 printf("RAW_READ_FIXED %s pin_to_macro=7 output_latency=16 actual_ports=%u expected_ports=%u compared_cycles=%u bad=%u\n",bad==0&&actual_total==103244&&expected_total==103244?"PASS":"FAIL",actual_total,expected_total,compared_cycles,bad);
 return bad==0&&actual_total==103244&&expected_total==103244?0:1;
}
