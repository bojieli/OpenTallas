#include "Vot_qwen_tp8_k_request_adapter.h"
#include "verilated.h"
#include <cstdio>
#include <string>
int main(int argc,char**argv){
 std::string mode=argc>1?argv[1]:"capacity";
 Vot_qwen_tp8_k_request_adapter t;
 unsigned errors=0;
 auto tick=[&](){t.clk=0;t.eval();t.clk=1;t.eval();};
 t.rst_n=0;t.start=0;t.raw_valid=0;t.raw_wrong_type=0;t.req_ready=0;t.rsp_valid=0;
 t.epoch=17;t.layer=6;t.rsp_epoch=17;t.rsp_layer=6;
 tick();tick();t.rst_n=1;t.start=1;tick();t.start=0;
 for(int i=0;i<128;i++){t.raw_valid=1;t.raw_t=i;tick();if(t.fault)errors++;}
 t.raw_valid=0;
 for(int i=0;i<1000;i++){t.clk=0;t.eval();if(!t.req_valid||t.req_t!=0||t.fault)errors++;tick();}
 if(mode=="capacity"){
  // Retain all 128 ordered requests through request and response retirement.
  // Responses overlap later requests, so all three queue counts are exercised.
  t.req_ready=1;
  for(int i=0;i<129;i++){
   t.clk=0;t.eval();if(i<128&&(!t.req_valid||t.req_t!=i))errors++;
   t.rsp_valid=i>0;t.rsp_t=i-1;t.eval();
   if(i>0&&!t.checked_rsp)errors++;
   tick();if(t.fault)errors++;
  }
  t.rsp_valid=0;t.req_ready=0;t.clk=0;t.eval();
  if(t.req_valid||t.accepted!=128)errors++;
  t.start=1;tick();t.start=0;t.raw_valid=1;t.raw_t=511;tick();t.raw_valid=0;t.clk=0;t.eval();
  if(t.fault||!t.req_valid||t.req_t!=511||t.accepted!=0)errors++;
 }else if(mode=="overrun"){
  t.raw_valid=1;t.raw_t=128;tick();
 }else if(mode=="busy_restart"){
  t.start=1;tick();
 }else if(mode=="unsolicited"){
  t.rsp_valid=1;t.rsp_t=0;tick();
 }else{
  t.req_ready=1;tick();t.req_ready=0;
  t.rsp_valid=1;t.rsp_t=mode=="order"?1:0;
  if(mode=="epoch")t.rsp_epoch=16;
  if(mode=="layer")t.rsp_layer=7;
  if(mode=="wrong_type"){
   tick(); // Retire one valid response first; the new raw request has room.
   t.rsp_valid=0;t.raw_valid=1;t.raw_wrong_type=1;
  }
  tick();
 }
 bool pass=errors==0&&(mode=="capacity"?!t.fault:bool(t.fault));
 std::printf("{\"scope\":\"FUNCTIONAL_K_ADAPTER_NOT_PHYSICAL\",\"mode\":\"%s\",\"passed\":%s,\"errors\":%u,\"fault\":%u,\"accepted\":%u}\n",mode.c_str(),pass?"true":"false",errors,unsigned(t.fault),unsigned(t.accepted));
 return pass?0:1;
}
