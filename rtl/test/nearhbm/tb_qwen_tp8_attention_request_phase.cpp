// Observe the source-derived command->ECTL3->K-face pipeline. No arithmetic
// results are supplied: this probe ends before the first K return is due.
#include "Vot_qwen_tp8_attention_service.h"
#include "verilated.h"
#include <cstdio>
int main(){
 Vot_qwen_tp8_attention_service t;unsigned cy=0;
 auto tick=[&](){t.clk=0;t.eval();t.clk=1;t.eval();cy++;};
 t.rst_n=0;t.request_valid=t.q_valid=t.k_rsp_valid=t.v_rsp_valid=0;
 t.k_req_ready=0xffffffff;t.v_req_ready=15;t.result_ready=1;
 t.request_epoch=17;t.request_layer=6;t.request_position=8191;t.fused_program_capability=1;
 t.q_beat=0;for(int i=0;i<16;i++)t.q_data[i]=0;
 for(int i=0;i<8;i++)tick();t.rst_n=1;for(int i=0;i<80;i++)tick();
 t.request_valid=1;t.clk=0;t.eval();if(!t.request_ready)return 2;
 unsigned command=cy;tick();t.request_valid=0;unsigned first=0,errors=0;
 for(unsigned step=0;step<20;step++){
  t.clk=0;t.q_valid=step>=1;t.q_beat=step?step-1:0;t.eval();
  if(t.k_req_valid){
   if(!first)first=cy-command;
   if(t.k_req_valid!=0xffffffffu)errors++;
  }
  tick();if(t.fault)errors++;
 }
 bool exact=first==9&&errors==0;
 std::printf("{\"scope\":\"SOURCE_DERIVED_REQUEST_PHASE_COMPONENT_ONLY\",\"first_k_request_edge_after_command\":%u,\"source_expected\":9,\"errors\":%u,\"exact\":%s}\n",first,errors,exact?"true":"false");
 return !exact;
}
