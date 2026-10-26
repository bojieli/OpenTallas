#include "Vot_qwen_tp8_k_request_static.h"
#include "verilated.h"
#include <deque>
#include <cstdio>
#include <string>
struct Return { unsigned at,tag; };
int main(int argc,char**argv){
 std::string mode=argc>1?argv[1]:"exact";
 Vot_qwen_tp8_k_request_static t;
 auto tick=[&](){t.clk=0;t.eval();t.clk=1;t.eval();};
 t.rst_n=0;t.start=0;t.raw_valid=0;t.raw_t=0;t.raw_wrong_type=0;
 t.req_ready=1;t.rsp_valid=0;t.rsp_t=0;t.rsp_epoch=17;t.rsp_layer=6;t.epoch=17;t.layer=6;
 tick();t.rst_n=1;t.start=1;tick();t.start=0;
 std::deque<Return> pending;unsigned issued=0,returned=0,errors=0;bool changed=false;
 bool previous_valid=false;unsigned previous_tag=0;
 // 8192 tagged rows: one/cycle bursts with statically assigned idle slots.
 // No waiting for a capacity/status/ready signal anywhere in the source.
 for(unsigned cy=0;cy<10000;cy++){
  t.clk=0;t.raw_valid=issued<8192 && cy%17!=16;t.raw_t=issued;
  if(t.raw_valid)issued++;
  t.raw_wrong_type=mode=="type"&&cy==8;t.req_ready=!(mode=="ready"&&cy==8);
  t.start=mode=="restart"&&cy==8;
  t.rsp_valid=!pending.empty()&&pending.front().at==cy;
  if(t.rsp_valid){t.rsp_t=pending.front().tag;pending.pop_front();}
  if(!changed&&cy>30&&t.rsp_valid&&mode=="missing"){t.rsp_valid=0;changed=true;}
  if(!changed&&cy>30&&t.rsp_valid&&mode=="epoch"){t.rsp_epoch=16;changed=true;}
  if(!changed&&cy>30&&t.rsp_valid&&mode=="order"){t.rsp_t^=1;changed=true;}
  if(mode=="early"&&cy==3){t.rsp_valid=1;t.rsp_t=0;}
  t.eval();
  if(mode=="exact"&&(bool(t.req_valid)!=previous_valid || (t.req_valid&&t.req_t!=previous_tag)))errors++;
  if(t.req_valid)pending.push_back({cy+16,unsigned(t.req_t)});
  if(t.checked_rsp)returned++;
  previous_valid=t.raw_valid;previous_tag=t.raw_t;
  tick();
  if(t.fault)break;
  if(issued==8192&&returned==8192)break;
 }
 bool exact=!t.fault&&errors==0&&returned==8192&&t.accepted==8192;
 std::printf("{\"mode\":\"%s\",\"exact\":%s,\"fault\":%u,\"issued\":%u,\"returned\":%u,\"errors\":%u}\n",mode.c_str(),exact?"true":"false",unsigned(t.fault),issued,returned,errors);
 return mode=="exact"?!exact:!t.fault;
}
