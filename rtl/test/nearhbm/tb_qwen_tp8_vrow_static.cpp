#include "Vot_qwen_tp8_vrow_static.h"
#include "verilated.h"
#include <deque>
#include <string>
#include <cstdio>
#ifndef PAIR
#define PAIR 0
#endif
struct Row{unsigned at,t,slot;bool hi;};
int main(int argc,char**argv){
 std::string mode=argc>1?argv[1]:"exact";unsigned ctx=argc>2?std::stoul(argv[2]):8192;
 Vot_qwen_tp8_vrow_static t;auto tick=[&](){t.clk=0;t.eval();t.clk=1;t.eval();};
 t.rst_n=0;t.start=0;t.context_len=ctx;t.epoch=17;
 t.lo_req_ready=t.hi_req_ready=t.out_ready=1;t.lo_rsp_valid=t.hi_rsp_valid=0;
 t.lo_rsp_t=t.hi_rsp_t=0;t.lo_rsp_slot=t.hi_rsp_slot=0;t.lo_rsp_epoch=t.hi_rsp_epoch=17;
 t.lo_exp=0x123456789abcdef0ULL;t.hi_exp=0xfedcba9876543210ULL;
 for(int i=0;i<32;i++)t.lo_vrow[i]=t.hi_vrow[i]=0;
 tick();t.rst_n=1;t.start=1;tick();t.start=0;
 unsigned tail=ctx%256,extra=tail>PAIR*128?tail-PAIR*128:0;if(extra>128)extra=128;
 unsigned expected=(ctx/256)*128+extra,issued=0,returned=0,errors=0,next=PAIR*128;
 if(!expected){std::printf("{\"mode\":\"%s\",\"pair\":%u,\"context\":%u,\"exact\":%s,\"fault\":%u,\"issued\":0,\"returned\":0,\"errors\":0}\n",mode.c_str(),PAIR,ctx,t.done&&!t.fault?"true":"false",unsigned(t.fault));return !t.done||t.fault;}
 std::deque<Row> pending;bool changed=false;
 for(unsigned cy=0;cy<10000;cy++){
  t.clk=0;t.lo_rsp_valid=t.hi_rsp_valid=0;t.lo_rsp_epoch=t.hi_rsp_epoch=17;
  t.lo_req_ready=t.hi_req_ready=!(mode=="ready"&&cy==128);t.out_ready=1;
  if(!pending.empty()&&pending.front().at==cy){
   auto r=pending.front();pending.pop_front();
   t.lo_rsp_valid=!r.hi;t.hi_rsp_valid=r.hi;
   t.lo_rsp_t=t.hi_rsp_t=r.t;t.lo_rsp_slot=t.hi_rsp_slot=r.slot;
   for(int i=0;i<32;i++)t.lo_vrow[i]=t.hi_vrow[i]=r.t*32+i;
   if(!changed&&mode=="missing"){t.lo_rsp_valid=t.hi_rsp_valid=0;changed=true;}
   if(!changed&&mode=="order"){t.lo_rsp_t^=1;t.hi_rsp_t^=1;changed=true;}
   if(!changed&&mode=="epoch"){t.lo_rsp_epoch=t.hi_rsp_epoch=16;changed=true;}
   if(!changed&&mode=="slot"){t.lo_rsp_slot^=1;t.hi_rsp_slot^=1;changed=true;}
   if(!changed&&mode=="consumer"){t.out_ready=0;changed=true;}
  }
  if(mode=="early"&&cy==4)t.lo_rsp_valid=1;
  t.eval();
  if(t.lo_req_valid||t.hi_req_valid){
   if(mode=="exact"&&(cy!=128+issued || t.req_t!=next || bool(t.hi_req_valid)!=bool(next&256)))errors++;
   pending.push_back({cy+17,unsigned(t.req_t),unsigned(t.req_slot),bool(t.hi_req_valid)});issued++;
   next=(next%128==127)?next+129:next+1;
  }
  if(t.out_valid){
   if(mode=="exact"){
    for(int i=0;i<32;i++)if(t.out_vrow[i]!=t.out_t*32+i)errors++;
    if(t.out_exp!=((t.out_t&256)?0xfedcba9876543210ULL:0x123456789abcdef0ULL))errors++;
    if(cy!=128+17+returned||t.out_epoch!=17)errors++;
   }
   returned++;
  }
  tick();if(t.fault||t.done)break;
 }
 bool exact=!t.fault&&errors==0&&t.done&&issued==expected&&returned==expected;
 std::printf("{\"mode\":\"%s\",\"pair\":%u,\"context\":%u,\"exact\":%s,\"fault\":%u,\"issued\":%u,\"returned\":%u,\"errors\":%u}\n",mode.c_str(),PAIR,ctx,exact?"true":"false",unsigned(t.fault),issued,returned,errors);
 return mode=="exact"?!exact:!t.fault;
}
