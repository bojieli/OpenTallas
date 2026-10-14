#pragma once
// Functional VM backing only. Every Q response is read from mutable VM;
// every commit ACK below follows an actual addressed write into that VM.
#include <array>
#include <bitset>
#include <cstdint>
#include <deque>
#include <stdexcept>
#include <vector>
#include <type_traits>
#include <utility>
namespace qwen_native_services {
template<class F,class=void> struct HasQTag:std::false_type{};
template<class F> struct HasQTag<F,std::void_t<decltype(std::declval<F>().q_vm_req_tag)>>:std::true_type{};
template<class F,class=void> struct HasAttnTag:std::false_type{};
template<class F> struct HasAttnTag<F,std::void_t<decltype(std::declval<F>().attn_vm_tag)>>:std::true_type{};
struct Ack {uint64_t due;unsigned beat,epoch,layer;uint64_t tag=0;};
struct QResponse {uint64_t due;unsigned epoch,chunk;std::array<uint32_t,64> data;uint64_t tag=0;};
struct Write {uint64_t edge;unsigned address,beat,epoch,layer;std::array<uint32_t,16> data;uint64_t tag=0;};
class VmReceiver {
public:
 std::vector<uint32_t>& vm;std::bitset<512> qr_written;
 std::deque<Ack> acks;std::deque<QResponse> responses;
 std::vector<Write> writes;
 uint64_t edge=0,q_requests=0,q_responses=0,commit_acks=0;
 unsigned epoch=0,layer=0,token=0,position=255;bool reserved=false,stalls=false;
 unsigned ack_delay=1; // registered ACK after an actual write edge; no inferred commit
 explicit VmReceiver(std::vector<uint32_t>& values):vm(values){}
 void reserve(unsigned e,unsigned l,unsigned t=0,unsigned p=255){
  if(!acks.empty()||!responses.empty())throw std::runtime_error("new VM identity before drain");
  epoch=e;layer=l;token=t;position=p;reserved=true;qr_written.reset();
 }
 void observe_write(unsigned address){if(address>=13696&&address<14208)qr_written.set(address-13696);}
 template<class Front> void drive(Front& f){
  f.qr_vm_committed=reserved&&qr_written.all();
  f.q_vm_req_ready=responses.empty()&&(!stalls||edge%7!=0);
  f.q_vm_rsp_v=0;f.attn_commit_valid=0;
  f.attn_vm_ready=reserved&&(!stalls||edge%5!=0);
  if(!responses.empty()&&responses.front().due<=edge){auto&r=responses.front();
   f.q_vm_rsp_v=1;
   if constexpr(HasQTag<Front>::value)f.q_vm_rsp_tag=r.tag;else f.q_vm_rsp_epoch=r.epoch;
   f.q_vm_rsp_chunk=r.chunk;
   for(unsigned i=0;i<64;i++)f.q_vm_rsp_data[i]=r.data[i];
  }
  if(!acks.empty()&&acks.front().due<=edge){auto&a=acks.front();
   f.attn_commit_valid=1;f.attn_commit_beat=a.beat;
   if constexpr(HasAttnTag<Front>::value)f.attn_commit_tag=a.tag;
   else{f.attn_commit_epoch=a.epoch;f.attn_commit_layer=a.layer;}
  }
 }
 // Call after all low-phase model interfaces settle, before rising eval.
 template<class Front> void sample(Front& f){
  if(f.q_vm_rsp_v){if(responses.empty())throw std::runtime_error("unowned Q VM response");responses.pop_front();++q_responses;}
  if(f.attn_commit_valid){if(acks.empty())throw std::runtime_error("unowned attention ACK");acks.pop_front();++commit_acks;}
  if(f.q_vm_req_v&&f.q_vm_req_ready){
   if(!reserved||f.q_vm_req_epoch!=epoch||f.q_vm_req_chunk>7||
      f.q_vm_req_a0!=13696+64*f.q_vm_req_chunk||f.q_vm_req_a1!=f.q_vm_req_a0+1)
    throw std::runtime_error("Q VM request ownership/address mismatch");
   QResponse r{edge+1,unsigned(f.q_vm_req_epoch),unsigned(f.q_vm_req_chunk),{}};
   if constexpr(HasQTag<Front>::value){
    r.tag=f.q_vm_req_tag;
    uint64_t expected=(uint64_t(epoch)<<43)|(uint64_t(layer+1)<<37)|(uint64_t(token)<<19)|(uint64_t(position)<<6);
    if(r.tag!=expected)throw std::runtime_error("Q VM accepted fullTAG59 identity mismatch");
   }
   for(unsigned i=0;i<64;i++)r.data[i]=vm.at(f.q_vm_req_a0+i);
   responses.push_back(r);++q_requests;
  }
  if(f.attn_vm_valid&&f.attn_vm_ready){
   if(!reserved||f.attn_vm_epoch!=epoch||f.attn_vm_layer!=layer||
      f.attn_vm_word_addr!=3167+f.attn_vm_beat)
    throw std::runtime_error("attention VM ownership/address mismatch");
   Write w{edge,unsigned(f.attn_vm_word_addr)*16,unsigned(f.attn_vm_beat),epoch,layer,{}};
   if constexpr(HasAttnTag<Front>::value){
    w.tag=f.attn_vm_tag;
    uint64_t expected=(uint64_t(epoch)<<43)|(uint64_t(layer+1)<<37)|(uint64_t(token)<<19)|(uint64_t(position)<<6);
    if(w.tag!=expected)throw std::runtime_error("attention VM accepted write fullTAG59 identity mismatch");
   }
   for(unsigned i=0;i<16;i++)w.data[i]=f.attn_vm_data[i];
   writes.push_back(w); // store_after_edge commits exactly this captured transaction
  }
 }
 void store_after_edge(){
  if(!writes.empty()&&writes.back().edge==edge){auto&w=writes.back();
   for(unsigned i=0;i<16;i++)vm.at(w.address+i)=w.data[i];
   acks.push_back({edge+ack_delay,w.beat,w.epoch,w.layer,w.tag});
  }
  ++edge;
 }
};
// The caller supplies the actual compiled production kernel class. There is no
// arithmetic/result substitute here. Keep both clocks LOW while settling;
// sample the final interfaces, then evaluate both rising edges with them held.
template<class Front,class Kernel> void settle(Front& f,Kernel& k){
 auto connect=[&](){
  k.request_valid=f.kernel_request_valid;k.request_epoch=f.kernel_request_epoch;
  k.request_layer=f.kernel_request_layer;k.request_position=f.kernel_request_position;
  k.fused_program_capability=f.kernel_capability;k.q_valid=f.kernel_q_valid;k.q_beat=f.kernel_q_beat;
  for(unsigned i=0;i<16;i++)k.q_data[i]=f.kernel_q_data[i];
  k.result_ready=f.kernel_result_ready;
  f.kernel_ready=k.request_ready;f.kernel_busy=k.busy;f.kernel_fault=k.fault;
  f.kernel_done=k.result_done;f.kernel_q_ready=k.q_ready;
  f.active_epoch=k.active_epoch;f.active_layer=k.active_layer;
  f.kernel_result_valid=k.result_valid;f.kernel_result_beat=k.result_beat;
  f.kernel_result_epoch=k.result_epoch;f.kernel_result_layer=k.result_layer;
  for(unsigned i=0;i<16;i++)f.kernel_result_data[i]=k.result_data[i];
 };
 auto state=[&](){std::vector<uint32_t>s={unsigned(f.kernel_request_valid),unsigned(f.kernel_q_valid),
  unsigned(f.kernel_result_ready),unsigned(f.native_ready),unsigned(f.native_idle),unsigned(f.q_vm_req_v),
  unsigned(k.request_ready),unsigned(k.q_ready),unsigned(k.result_valid),unsigned(k.result_beat),
  unsigned(k.result_epoch),unsigned(k.result_layer),unsigned(k.result_done),unsigned(k.busy),unsigned(k.fault)};
  for(unsigned i=0;i<16;i++){s.push_back(f.kernel_q_data[i]);s.push_back(k.result_data[i]);}return s;};
 if(f.clk||k.clk)throw std::runtime_error("cross-model settle requires low clocks");
 for(unsigned n=0;n<16;n++){auto before=state();connect();f.eval();k.eval();connect();if(state()==before)return;}
 throw std::runtime_error("native kernel/frontend interfaces did not settle");
}
}
