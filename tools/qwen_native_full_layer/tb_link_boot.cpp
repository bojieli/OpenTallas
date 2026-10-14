#include "Vot_qwen_tp8_native_services_frontend.h"
#include "Vot_qwen_tp8_attention_service.h"
#include "services_vm_adapter.hpp"
#include <cstdio>
int main(){
 Vot_qwen_tp8_native_services_frontend f;Vot_qwen_tp8_attention_service k;
 std::vector<uint32_t> vm(56816);qwen_native_services::VmReceiver mem(vm);
 f.rst_n=k.rst_n=0;f.fused_program_capability=1;
 f.native_xbase=13696;f.native_obase=3167;f.native_nout=512;f.native_k=128;f.native_pos=255;
 f.native_go=0;f.epoch_begin=0;f.row_ready=0;f.store_ack_v=0;
 k.k_req_ready=0;k.v_req_ready=0;k.k_rsp_valid=0;k.v_rsp_valid=0;
 unsigned premature=0;
 for(unsigned cycle=0;cycle<1100;cycle++){
  if(cycle==8)f.rst_n=k.rst_n=1;
  f.clk=k.clk=0;mem.drive(f);qwen_native_services::settle(f,k);
  if(cycle==100){if(!f.epoch_ready)return 2;f.epoch=17;f.layer=0;f.pos=255;f.epoch_begin=1;mem.reserve(17,0);}
  if(cycle==101)f.epoch_begin=0;
  qwen_native_services::settle(f,k);mem.sample(f);
  premature+=f.native_ready||f.native_completed||f.attn_vm_valid;
  f.clk=k.clk=1;f.eval();k.eval();mem.store_after_edge();
  if(f.fault||k.fault)return 3;
 }
 printf("{\"scope\":\"ACTUAL_KERNEL_FRONTEND_LINK_BOOT_ONLY\",\"cycles\":1100,\"fault\":0,\"premature_readiness_or_commit\":%u,\"whole_layer\":false}\n",premature);
 return premature?1:0;
}
